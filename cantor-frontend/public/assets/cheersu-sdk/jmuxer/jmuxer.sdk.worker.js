import MtspParser from "./mtsp";
//
let parser = new MtspParser();

self.onmessage = function (e) {
  // 接收并处理从Vue组件发送的数据
  // 将处理结果发送回Vue组件
  parser.parse(
    e.data,
    (hdr, payload) => {
      self.postMessage({
        status: 1,
        hdr,
        payload,
      });
    },
    (error) => {
      self.postMessage({
        status: 0,
        error,
      });
    }
  );
};
