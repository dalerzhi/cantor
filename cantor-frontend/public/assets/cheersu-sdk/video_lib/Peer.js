import EnhancedEventEmitter from "./EnhancedEventEmitter";
import Logger from "./Logger";

const logger = new Logger("Peer");

export class Peer extends EnhancedEventEmitter {
  constructor(id, cb) {
    super(logger);

    this.id_ = id;
    this.media_streams_ = new Map();
    this.onleave = null;
    this.callback = cb;
  }

  get id() {
    return this.id_;
  }
  leave() {
    if (this.onleave) {
      this.onleave(this.id);
    }
  }
  sendMessage(msg) {
    if (this.datachannel_ !== undefined) {
      const { readyState } = this.datachannel_;
      if (readyState === "open") {
        if (this.isStringSmallerThan16KB(msg)) {
          this.datachannel_.send(msg);
        } else {
          this.safeEmit("on-peer-error-status", {
            type: "dataChannelSendState",
            status: -1,
            message: "dataChannel发送消息太大: 最大值为 16kib",
          });
        }
      } else {
        this.safeEmit("on-peer-error-status", {
          type: "dataChannelReadyState",
          status: readyState,
          message: "dataChannel失败: 状态码为:" + readyState,
        });
      }
    }
  }
  isStringSmallerThan16KB(str) {
    try {
      const blob = new Blob([str]);
      return blob.size < 16 * 1024; // 16 KiB is 16 * 1024 bytes
    } catch (e) {
      return false;
    }
  }
  setDataChannel(datachannel) {
    if (datachannel !== undefined && datachannel != null) {
      this.datachannel_ = datachannel;
      this.datachannel_.onopen = this._onDataChannelOpen.bind(this);
      this.datachannel_.onmessage = this._onDataChannelMessage.bind(this);
      this.datachannel_.onerror = (e) => {
        logger.debug("dataChannel error");
        this.safeEmit("on-peer-error-status", {
          type: "dataChannel",
          status: "error",
          message: "dataChannel失败: " + JSON.stringify(e),
        });
      };
    }
  }
  /* Inner method */
  setId(id) {
    this.id_ = id;
  }
  leaveNotify() {
    this.safeEmit("on-user-leave-notify", { Peer: this });
  }
  rotationNotify(obj) {
    this.safeEmit("on-user-rotation-notify", obj);
  }
  setResolv(resolv) {
    this.resolv = resolv;
  }
  setMediaStream(s, transceiver) {
    this.transceiver_ = transceiver;
    this.media_stream_ = s;
    logger.debug("setMediaStream.......1");
    if (this.resolv) {
      logger.debug("setMediaStream.......2");
      this.resolv(this.media_stream_);
    }
  }
  _onDataChannelOpen(event) {
    this.callback({ type: "data-channel-open", message: "dataChannel 完成" });
    logger.debug("onDataChannelOpen!");
  }
  _onDataChannelMessage(event) {
    this.safeEmit("on-data-channel-message", event);
    logger.debug("DataChannel recv message:" + event.data);
  }
}
