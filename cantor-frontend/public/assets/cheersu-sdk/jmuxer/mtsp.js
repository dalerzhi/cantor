import BlockQueueBuffer from "./bloc";
class MtspParser {
  constructor() {
    this.buffer = new BlockQueueBuffer(); // 使用块队列替代单一缓存
    this.header = null;
    this.expectedPayload = 0;
    //this.currentReadPos = 0; // 在块队列中的全局读取位置
    this.first = false;
  }

  parse(data, callback, errCallback) {
    //console.log("parse dataLength:", data, data.byteLength);
    this.buffer.append(data); // 直接追加原始数据块（零拷贝）
    // 检查是否可以解析
    let availableBytes = this.buffer.getTotalBytes("available");
    if (!this.header) {
      // 尚未解析头部：检查是否至少有16字节可用
      if (availableBytes < 16) {
        // console.log("this.buffer:" + availableBytes + " lt 16 bytes.");
        return;
      }
      // parse header
      this.parseHeader();
      availableBytes -= 16;
    }
    //console.log("availableBytes :" + availableBytes + " expectedPayload:" + this.expectedPayload, Date.now());
    // 已解析头部：检查是否足够读取有效载荷
    if (availableBytes >= /*this.currentReadPos +*/ this.expectedPayload) {
      const payloadData = this.buffer.read(this.expectedPayload);
      callback(this.header, payloadData);
      // 重置状态
      this.header = null;
      this.expectedPayload = 0;
      //this.currentReadPos = 0; // 从头开始读取下一个数据包
    } else {
      if (availableBytes > 50000 && !this.first) {
        this.first = true;
        console.log(
          this.header.id.streamid + "max availableBytes",
          "availableBytes => " + availableBytes,
          "this.expectedPayload==>",
          this.expectedPayload,
          "this.header",
          JSON.stringify(this.header)
        );
        errCallback();
      }
      //console.log("event.data2 availableBytes :" +this.header.id.streamid + availableBytes + " expectedPayload:" + this.expectedPayload, Date.now());
    }
  }

  parseHeader() {
    // 从块队列中读取16字节
    const headerData = this.buffer.read(16);
    const view = new DataView(headerData.buffer, 0, 16);

    this.header = {
      version: (view.getUint8(0) >> 6) & 0x03,
      mark: (view.getUint8(0) >> 5) & 0x01,
      pt: view.getUint8(0) & 0x1f,
      x: (view.getUint8(1) >> 7) & 0x01,
      reserved: view.getUint8(1) & 0x7f,
      seq_no: view.getUint16(2) & 0xffff,
      timestamp: view.getUint32(4),
      id: {
        streamid: view.getUint32(8),
        messageid: view.getUint32(8),
      },
      length: view.getUint32(12),
    };

    this.expectedPayload = this.header.length;
    //this.currentReadPos = 16; // 更新全局读取位置
  }
  clear() {
    this.buffer = null; // 使用块队列替代单一缓存
    this.header = null;
    this.expectedPayload = 0;
  }
}
export default MtspParser;
