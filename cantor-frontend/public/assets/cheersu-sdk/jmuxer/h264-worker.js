import MtspParser from "./mtsp";
let parser = new MtspParser();
onmessage = function (data) {
  parser.parse(data, (hdr, payload) => {
    postMessage({ hdr, payload });
  });
  // 将结果发送回主线程
};
