import MtspParser from "./mtsp";
import Worker from "./jmuxer.sdk.worker";
class ParserWorker {
  constructor() {
    this.parser = new MtspParser();
    this.worker = new Worker();
    this.isWorker = this.isWorkerSupported();
    this.worker.onmessage = this.workerOnmessage.bind(this);
    this.onmessageBack = null;
  }

  postMessage(data) {
    if (this.isWorker) {
      this.worker.postMessage(data);
    } else {
      this.parser.parse(
        data,
        (hdr, payload) => {
          let data = {
            status: 1,
            hdr,
            payload,
          };
          if (this.onmessageBack) {
            this.onmessageBack(data);
          }
        },
        (error) => {
          let data = {
            status: 0,
            error,
          };
          if (this.onmessageBack) {
            this.onmessageBack(data);
          }
        }
      );
    }
  }
  workerOnmessage(e) {
    if (e) {
      const data = e.data;
      if (this.onmessageBack) {
        this.onmessageBack(data);
      }
    }
  }
  isWorkerSupported() {
    try {
      // 尝试创建一个 Worker 对象
      new Worker();
      return true; // 如果没有抛出错误，说明支持 Worker
    } catch (e) {
      return false; // 如果抛出错误，说明不支持 Worker
    }
  }
  clear() {
    console.log("worker clear");
    this.worker && this.worker.terminate();
    this.worker = null;
    this.parser && this.parser.clear();
    this.parser = null;
  }
}

export default ParserWorker;
