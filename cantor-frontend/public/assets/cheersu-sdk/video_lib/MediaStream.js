import EnhancedEventEmitter from "./EnhancedEventEmitter";
import Logger from "./Logger";

const logger = new Logger("MediaStream");

export default class MediaStream extends EnhancedEventEmitter {
  constructor(id, mt, owner) {
    super(logger);
    this.id_ = id;
    this.owner_ = owner;
    this.media_type_ = mt;
    this.video_image_param = [];
  }

  setCodec(c) {
    this.codec_ = c;
  }
  get codec() {
    return this.codec_;
  }

  get media_type() {
    return this.media_type_;
  }
  get id() {
    return this.id_;
  }
  get owner() {
    return this.owner_;
  }

  remove() {
    this.safeEmit("on-stream-removed");
  }
}
