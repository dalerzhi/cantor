export class MediaConstraints {
  constructor(enable_audio, enable_video) {
    this.video = enable_video;
    this.audio = enable_audio;
  }
  setHeight(h) {
    this.height_ = h;
  }
  setWidth(w) {
    this.width_ = w;
  }

  get height() {
    return this.height_;
  }

  get width() {
    return this.width_;
  }
}
