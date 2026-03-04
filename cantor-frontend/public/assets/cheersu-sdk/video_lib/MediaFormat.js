export class AudioCodec {
  constructor(name, channels, st) {
    this.name_ = name;
    this.channels_ = channels;
    this.sample_rate_ = st;
  }

  get name() {
    return this.name_;
  }
  get channels() {
    return this.channels_;
  }
  get sample_rate() {
    return this.sample_rate_;
  }
}

export class VideoCodec {
  constructor(name, profile) {
    this.name_ = name;
    this.profile_ = profile;
  }

  get name() {
    return this.name_;
  }
  get profile() {
    return this.profile_;
  }
}

export class VideoImageParams {
  constructor(w, h, fps, bps, gop, rid) {
    this.width_ = w;
    this.height_ = h;
    this.fps_ = fps;
    this.bps_ = bps;
    this.gop_ = gop;
    this.rid_ = rid;
  }

  get width() {
    return this.width_;
  }

  get height() {
    return this.height_;
  }

  get fps() {
    return this.fps_;
  }
  get gop() {
    return this.gop_;
  }
  get bps() {
    return this.bps_;
  }
  get rid() {
    return this.rid_;
  }
}
