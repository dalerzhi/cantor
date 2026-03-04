class UserMedia {
  constructor(videoStatus = false, audioStatus = false) {
    this.videoStatus = videoStatus || false;
    this.audioStatus = audioStatus || false;
  }
  setUserMedia(status, type) {
    if (![true, false].includes(status)) {
      throw new Error("状态只能为 true 和 false");
    }
    if (type) {
      if (["audio", "video"].includes(type)) {
        if (type === "audio") {
          this.audioStatus = status;
        } else if (type === "video") {
          this.videoStatus = status;
        }
      } else {
        throw new Error("类型只能为 audio 和 video");
      }
    } else {
      this.audioStatus = status;
      this.videoStatus = status;
    }
  }
  getUserMedia() {
    return {
      audio: this.audioStatus,
      video: this.videoStatus,
    };
  }
}
export { UserMedia };
