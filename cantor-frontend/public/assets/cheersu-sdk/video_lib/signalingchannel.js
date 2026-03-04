import EnhancedEventEmitter from "./EnhancedEventEmitter";
import Logger from "./Logger";
import io from "socket.io-client";

const logger = new Logger("SignalingChannel");

// This class implements a signaling channel based on WebSocket.
export class SignalingChannel extends EnhancedEventEmitter {
  constructor(wssUrl) {
    super(logger);

    this.wssUrl_ = wssUrl;
    this.roomId_ = null;
    this.clientId_ = null;
    this.sock_ = null;
    this.opened_ = false;
  }

  open(roomid, peerid) {
    this.roomId_ = roomid;
    this.clientId_ = peerid;

    return new Promise((resolve, reject) => {
      logger.debug("Opening signaling channel.wss=" + this.wssUrl_);

      let options = {
        reconnect: true,
        rejectUnauthorized: false,
      };

      this.sock_ = io(this.wssUrl_, options);

      this.sock_.on("connect", () => {
        logger.debug("Signaling channel opened. ready to probe.");

        this.opened_ = true;

        let req = {};
        req.roomid = this.roomId_;
        req.peerid = this.clientId_;
        this.sock_.emit("probe_req", req);

        this.sock_.on("probe_res", (res) => {
          logger.debug(JSON.stringify(res));
          if (res.result !== 0) {
            logger.error("socket.io probe failed. result=" + res.result);
            reject("socket.io probe failed. result=" + res.result);
          } else {
            resolve();
          }
        });
      });

      this.sock_.on("connect_error", (error) => {
        logger.error("connect error===" + error);
        reject("connect error===" + error);
      });

      this.sock_.on("error", (error) => {
        logger.debug("error === " + error);
      });

      this.sock_.on("reconnect", () => {
        logger.debug("reconnect ....");
      });

      this.sock_.on("disconnect", () => {
        logger.debug("disconnect");
      });
    });
  }

  register(res_event) {
    return new Promise((resolve, reject) => {
      this.sock_.on(res_event, (res) => {
        if (res.result !== 0) {
          reject("The request failed.result=" + res.result);
        } else {
          resolve(res);
        }
      });
    });
  }

  close(async) {
    if (this.sock_) {
      this.sock_.close();
      this.sock_ = null;
    }
  }

  send(event, data) {
    logger.debug("C->WSS: " + data);

    var wssMessage = {
      roomid: this.roomId_,
      peerid: this.clientId_,
      data: data,
    };
    this.sock_.emit(event, wssMessage);
  }
}
