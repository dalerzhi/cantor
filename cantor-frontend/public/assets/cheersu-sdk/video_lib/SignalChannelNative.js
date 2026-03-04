import EnhancedEventEmitter from "./EnhancedEventEmitter";
import Logger from "./Logger";
import BrowserWebSocket from "browser-websocket";

const logger = new Logger("SignalChannelNative");

export class SignalChannelNative extends EnhancedEventEmitter {
  constructor(wssUrl, wssUrlList, cb) {
    super(logger);

    this.wssUrl_ = wssUrl;
    this.wssUrlList_ = wssUrlList;
    this.sock_ = undefined;
    this.sents_ = new Map();
    this.reconnect_timer_ = undefined;
    this.statusCoonect = true;
    this.ChannelConnState = {
      Closed: 1,
      Connecting: 2,
      Connected: 3,
      Reconnecting: 4,
      ReconnectingTimeout: 5,
    };
    /**
     * The connection state:
     * 1: Closed.
     * 2: Connecting.
     * 3: Connected.
     * 4: Reconnecting
     * 5: ReconnectingTimeout
     */
    this.connState = this.ChannelConnState.Closed;
    this.timerTimeout = null;
    this.callback = cb;
  }

  open() {
    return new Promise((resolve, reject) => {
      this.connState = this.ChannelConnState.Connecting;
      this.sock_ = new BrowserWebSocket(this.wssUrl_);
      logger.debug("Open the signal channel...");
      this.sock_.on(
        "open",
        function (e) {
          this.callback({
            type: "signaling-connected",
            message: "信令连接完成",
          });
          let oldConnState = this.connState;
          this.connState = this.ChannelConnState.Connected;
          logger.debug(
            "Signal channel open success.oldConnState:" + oldConnState
          );
          if (oldConnState === this.ChannelConnState.Connecting) {
            // First reconnect success.
            resolve("success");
          } else if (oldConnState === this.ChannelConnState.Reconnecting) {
            // fast reconnect success.
            this.safeEmit("fast-reconnect-success");
          }
        }.bind(this)
      );

      this.sock_.on(
        "message",
        function (e) {
          var message = e.data;
          logger.debug("WSS->C" + message);
          var res = JSON.parse(message);
          let key = res.messageID + "";
          if (res.messageID !== 1004) {
            key = key + ":" + res.timestamp;
          }
          if (this.sents_.has(key)) {
            let ctx = this.sents_.get(key);
            if (ctx !== undefined) {
              this.sents_.delete(key);
              ctx.callback(res);
            }
          } else {
            this.safeEmit("message-notify", res);
          }
          this.statusCoonect = true;
          if (res.messageID === 1033) {
            this.statusCoonect = false;
          }
        }.bind(this)
      );
      this.sock_.on(
        "close",
        function (e) {
          logger.debug("code:" + e.code + " reason:" + e.reason);
          // fast reconnect.
          if (
            this.connState === this.ChannelConnState.Connected ||
            this.connState === this.ChannelConnState.Reconnecting ||
            this.connState === this.ChannelConnState.Connecting
          ) {
            this.connState = this.ChannelConnState.Reconnecting;
            logger.debug("this.statusCoonect: " + this.statusCoonect);
            if (this.statusCoonect) {
              logger.debug("Ready to reconnect channel...");
              this.reconnect();
            }
          }
          /*
                else {
                    if (this.connState === this.ChannelConnState.Connecting){
                        reject('Connect failed!');
                    }else{
                        if (this.on_connection_closed !== null
                            && this.connState !== this.ChannelConnState.Closed) {
                            this.close();
                            this.on_connection_closed();
                        }
                    }
                }
                */
        }.bind(this)
      );

      this.sock_.on(
        "error",
        function (e) {
          logger.debug("WebSocket error: ", e);
          this.safeEmit("on-signal-error-status", {
            type: "websocket",
            status: e.type,
            message: "websocket 连接失败",
          });
          if (this.connState === this.ChannelConnState.Connecting) {
            reject("websocket Connect error!");
          }
          /*
                else {
                    if (this.on_connection_closed !== null
                        && this.connState !== this.ChannelConnState.Closed) {
                        this.close();
                        this.on_connection_closed();
                    }
                }
                */
        }.bind(this)
      );

      // Resend
      this.timer_ = setInterval(() => {
        for (var [key, value] of this.sents_) {
          var nowms = new Date().getTime() & 0xffffffff;
          nowms = nowms >>> 0;

          if (value.sent_times < 3 && value.sent_times > 0) {
            if (value.sent_time + 2000 <= nowms) {
              value.sent_times++;
              value.sent_time = nowms;
              if (value.is_resend) {
                logger.debug(
                  "resend times:" + value.sent_times + " C->WSS: " + value.msg
                );
                this.sock_.emit(value.msg);
              }
            }
          } else {
            logger.debug("Message timeout: " + value.msg);
            this.sents_.delete(key);
            var res = {
              result: "Client message timeout:" + value.msg,
            };
            value.callback(res);
          }
        }
      }, 5000);
    });
  }

  send(req_msg, res_fun, is_resend) {
    if (this.connState !== this.ChannelConnState.Connected) {
      logger.warn(
        "The signal channel is not connected. current state:" + this.connState
      );
      return;
    }
    var msg = JSON.stringify(req_msg.req_msg);
    if (req_msg.req_msg.messageID !== 1521) {
      logger.debug("C->WSS: " + msg);
    }
    this.sock_.emit(msg);
    if (req_msg.res_key !== undefined) {
      var nowms = new Date().getTime() & 0xffffffff;
      nowms = nowms >>> 0;

      var sent_msg = {
        callback: res_fun,
        timestamp: req_msg.req_msg.timestamp,
        msg: msg,
        sent_times: 1,
        sent_time: nowms,
        resend: is_resend === undefined ? true : false,
      };

      var new_key = req_msg.res_key;
      if (req_msg.req_msg.messageID !== 1003) {
        new_key = new_key + ":" + sent_msg.timestamp;
      }
      this.sents_.set(new_key, sent_msg);
    }
  }

  close() {
    if (this.connState === this.ChannelConnState.Closed) {
      return;
    }

    logger.debug("Close native signal channel.");
    this.connState = this.ChannelConnState.Closed;

    if (this.timer_ !== undefined) {
      clearInterval(this.timer_);
      this.timer_ = undefined;
    }

    if (this.reconnect_timer_ !== undefined) {
      clearTimeout(this.reconnect_timer_);
      this.reconnect_timer_ = undefined;
    }

    if (this.sock_ !== undefined) {
      this.sock_.close();
      this.sock_ = undefined;
    }

    this.sents_.clear();
  }
  reconnect() {
    this.reconnect_timer = setTimeout(() => {
      if (this.sock_ !== undefined) {
        logger.debug("Signal Channel reconnecting ...");
        this.sock_.reconnect();
        /*
                if(!this.timerTimeout) {
                    this.timerTimeout = setTimeout(() => {
                        logger.debug('Reconnecting timeout....state:' + this.connState);
                        if(this.connState === this.ChannelConnState.Reconnecting) {
                            logger.debug('Reconnecting timeout....');
                            this.sock_.close();
                            this.reconnect();
                            this.timerTimeout = null;
                        }
                    }, 2000)
                }
                */
      }
    }, 2000);
  }
  getConnState() {
    return this.connState;
  }
  getWebSocketState() {
    return this.sock_.ws.readyState;
  }
}
