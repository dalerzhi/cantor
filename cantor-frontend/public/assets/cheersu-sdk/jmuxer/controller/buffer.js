import * as debug from "../util/debug";
import Event from "../util/event";
import { appendByteArray } from "../util/utils.js";

export default class BufferController extends Event {
  constructor(sourceBuffer, type, node) {
    super("buffer");

    this.type = type;
    this.queue = new Uint8Array();

    this.cleaning = false;
    this.pendingCleaning = 0;
    this.cleanOffset = 30;
    this.cleanRanges = [];

    this.sourceBuffer = sourceBuffer;
    this.clearEndTime = 10;
    this.lastTime = Date.now();
    this.sourceBuffer.addEventListener("updateend", () => {
      // console.log('updateend-now',this.pendingCleaning, this.cleanRanges.length, this.sourceBuffer.buffered.length)
      // if (this.pendingCleaning > 0) {
      //   this.initCleanup(this.pendingCleaning);
      //   this.pendingCleaning = 0;
      // }
      // console.log(Date.now() - this.lastTime, "Date.now() - this.lastTime");
      // const lastRange = sourceBuffer.buffered.length - 1;
      // console.log("sourceBuffer.buffered.end(lastRange)", sourceBuffer.buffered.end(lastRange) - sourceBuffer.buffered.start(0));
      if (Date.now() - this.lastTime > 5 * 1000) {
        this.lastTime = Date.now();
        this.resetClearData(this.sourceBuffer, node);
      }
      this.cleaning = false;
      this.timer = null;
      if (this.cleanRanges.length) {
        this.doCleanup();
        return;
      }
    });
    // const videoElement = document.getElementById(node);
    // let lastCleanTime = 0;
    // videoElement.addEventListener('timeupdate', () => {
    //   const currentTime = videoElement.currentTime;
    //   // 每5秒尝试清理一次
    //   if (currentTime - lastCleanTime > 5) {
    //     lastCleanTime = currentTime;
    //
    //     if (!sourceBuffer.updating && sourceBuffer.buffered.length > 0) {
    //       const bufferedEnd = sourceBuffer.buffered.end(sourceBuffer.buffered.length - 1);
    //       console.log('timeupdate', bufferedEnd, currentTime)
    //       // 如果缓冲区间超过20秒，清理前面的
    //       if (bufferedEnd - currentTime > 20) {
    //
    //         const removeEnd = currentTime - 5; // 保留当前时间前5秒
    //         if (removeEnd > sourceBuffer.buffered.start(0)) {
    //           sourceBuffer.remove(sourceBuffer.buffered.start(0), removeEnd);
    //         }
    //       }
    //     }
    //   }
    // });
    this.sourceBuffer.addEventListener("error", (err) => {
      console.log(err, "updateend-now-err");
      this.dispatch("error", {
        type: this.type,
        name: "buffer",
        error: "buffer error",
      });
    });
  }

  resetClearData(sourceBuffer, node) {
    if (!sourceBuffer.updating && sourceBuffer.buffered.length > 0) {
      // 可以在这里检查是否需要继续移除更多数据
      const videoElement = document.getElementById(node);
      if (videoElement) {
        const currentTime = videoElement.currentTime;
        // 只移除当前播放时间之前的数据
        const safetyMargin = 2; // 1秒安全边界
        const removeStart = sourceBuffer.buffered.start(0);
        if (currentTime > this.clearEndTime && currentTime - safetyMargin > 0) {
          sourceBuffer.remove(removeStart, currentTime - safetyMargin);
          this.clearEndTime = Math.floor(currentTime + 10);
          this.dispatch("clearAndFrame");
        }
        // console.log(document.hidden, videoElement.paused, videoElement.ended, Date.now());
        if ((!document.hidden && videoElement.paused) || videoElement.ended) {
          videoElement.play().catch((e) => {
            console.error("Playback failed to resume:", e);
            // 可能需要重新加载当前时间点的数据
          });
          // if (this.timer) {
          //   clearTimeout(this.timer);
          //   this.timer = null;
          // }
          // this.timer = setTimeout(() => {
          //   videoElement.play().catch((e) => {
          //     console.error("Playback failed to resume:", e);
          //     // 可能需要重新加载当前时间点的数据
          //   });
          // }, 200);
        }
      }
    }
  }
  destroy() {
    this.queue = null;
    this.sourceBuffer = null;
    this.offAll();
  }

  doCleanup() {
    console.log(this.cleanRanges.length, "this.cleanRanges.length");
    if (!this.cleanRanges.length) {
      this.cleaning = false;
      return;
    }
    let range = this.cleanRanges.shift();
    debug.log(`${this.type} remove range [${range[0]} - ${range[1]})`);
    this.cleaning = true;
    this.sourceBuffer.remove(range[0], range[1]);
  }

  initCleanup(cleanMaxLimit) {
    // console.log('cleanMaxLimit-now',
    //     cleanMaxLimit,
    //     this.sourceBuffer.updating,
    //     this.pendingCleaning,
    //     this.sourceBuffer.buffered,
    //     this.sourceBuffer.buffered.length,
    //     this.cleaning
    // )
    // try {
    //   if (
    //     this.sourceBuffer.buffered &&
    //     this.sourceBuffer.buffered.length &&
    //     !this.cleaning
    //   ) {
    //     for (let i = 0; i < this.sourceBuffer.buffered.length; ++i) {
    //       let start = this.sourceBuffer.buffered.start(i);
    //       let end = this.sourceBuffer.buffered.end(i);
    //       // console.log('cleanMaxLimit-now-1', start, end, this.cleanOffset);
    //       // if(end -3 > 0) {
    //         //this.sourceBuffer.remove(0, end - 3);
    //       // }
    //     }
    //     // this.doCleanup();
    //   }
    // } catch (e) {
    //   debug.error(
    //     `Error occured while cleaning ${this.type} buffer - ${e.name}: ${e.message}`
    //   );
    // }
  }
  initCleanup1(cleanMaxLimit) {
    console.log(
      "cleanMaxLimit",
      cleanMaxLimit,
      this.sourceBuffer.updating,
      this.pendingCleaning,
      this.sourceBuffer.buffered,
      this.sourceBuffer.buffered.length,
      this.cleaning
    );
    try {
      if (this.sourceBuffer.updating) {
        this.pendingCleaning = cleanMaxLimit;
        return;
      }
      if (
        this.sourceBuffer.buffered &&
        this.sourceBuffer.buffered.length &&
        !this.cleaning
      ) {
        for (let i = 0; i < this.sourceBuffer.buffered.length; ++i) {
          let start = this.sourceBuffer.buffered.start(i);
          let end = this.sourceBuffer.buffered.end(i);

          if (cleanMaxLimit - start > this.cleanOffset) {
            end = cleanMaxLimit - this.cleanOffset;
            if (start < end) {
              this.cleanRanges.push([start, end]);
            }
          }
        }
        this.doCleanup();
      }
    } catch (e) {
      debug.error(
        `Error occured while cleaning ${this.type} buffer - ${e.name}: ${e.message}`
      );
    }
  }
  doAppend() {
    // console.log(
    //   this.queue.length,
    //   this.sourceBuffer,
    //   this.sourceBuffer.updating,
    //   "doAppend"
    // );
    if (!this.queue.length) return;

    if (!this.sourceBuffer || this.sourceBuffer.updating) return;

    try {
      this.sourceBuffer.appendBuffer(this.queue);
      this.queue = new Uint8Array();
    } catch (e) {
      let name = "unexpectedError";
      if (e.name === "QuotaExceededError") {
        debug.log(`${this.type} buffer quota full`);
        name = "QuotaExceeded";
      } else {
        debug.error(
          `Error occured while appending ${this.type} buffer - ${e.name}: ${e.message}`
        );
        name = "InvalidStateError";
      }
      this.dispatch("error", {
        type: this.type,
        name: name,
        error: "buffer error",
      });
    }
  }

  feed(data) {
    this.queue = appendByteArray(this.queue, data);
  }
}
