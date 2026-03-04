class JmuxerMessage {
  constructor(version = 2) {
    this.version = version;
  }
  /**
   * 停止信令
   * @param peerID uid
   * @returns {{timestamp: number, messageID: number, version: number}}
   */
  curlStopRequest(peerID) {
    return {
      messageID: 1004,
      timestamp: new Date().getTime(),
      version: this.version,
      protoType: 2,
      peerID: peerID,
    };
  }
  /**
   * 调度心跳
   * @param peerID uid
   * @returns {{timestamp: number, messageID: number, version: number}}
   */
  curlHeartbeatRequest(peerID) {
    return {
      messageID: 1019,
      timestamp: new Date().getTime(),
      version: this.version,
      protoType: 2,
      peerID: peerID,
    };
  }

  /**
   * 翻页
   * @returns {{uid: string, frameRate: number, payloadType: number, instanceIds: [], width: number, messageID: number, bitrate: number, version: number, height: number, timestamp: number, peerID: string}}
   */
  curlPageTurnRequest() {
    return {
      uid: "",
      instanceIds: [],
      payloadType: 1,
      height: 0,
      width: 0,
      bitrate: 0,
      frameRate: 0,
      messageID: 1001,
      timestamp: new Date().getTime(),
      version: this.version,
      protoType: 2,
      subscribeType: 1,
      peerID: "",
    };
  }

  /**
   * 请求关键帧
   * @param streamIds
   * @returns {ArrayBuffer}
   */
  mUrlKeyframesRequest(streamIds = []) {
    let list = streamIds.map((x) => Number(x));
    let body = {
      streamIds: [...new Set(list)],
    };
    let obj = {
      version: 0,
      mark: 1,
      pt: 0,
      x: 0,
      reserved: 0,
      seq_no: 0,
      timestamp: new Date().getTime(),
      id: 1003,
    };
    // 创建一个缓冲区来存储二进制数据
    const buffer = new ArrayBuffer(1024); // 分配足够大的空间
    const view = new DataView(buffer);
    let offset = 0;

    // 按照字段顺序写入二进制数据
    // version: 假设是1字节无符号整数

    let version = (obj.version << 6) | (obj.marker << 5) | obj.pt;

    view.setUint8(offset, version);
    offset += 1;

    // reserved: 假设是1字节无符号整数
    view.setUint8(offset, obj.reserved);
    offset += 1;

    // seq_no: 假设是4字节无符号整数
    view.setUint16(offset, obj.seq_no, false); // true表示小端字节序
    offset += 2;

    // timestamp: 假设是4字节无符号整数
    view.setUint32(offset, obj.timestamp, false);
    offset += 4;

    // id: 假设是2字节无符号整数
    view.setUint32(offset, obj.id, false);
    offset += 4;
    const bodyStr = JSON.stringify(body);
    let length = bodyStr.length;
    // length: 假设是2字节无符号整数
    view.setUint32(offset, length, false);
    offset += 4;

    // body: 将JSON字符串转换为UTF-8编码的二进制数据

    const encoder = new TextEncoder();
    const bodyData = encoder.encode(bodyStr);

    // 将body数据写入缓冲区
    for (let i = 0; i < bodyData.length; i++) {
      view.setUint8(offset, bodyData[i]);
      offset += 1;
    }

    // 返回实际使用的缓冲区部分
    return buffer.slice(0, offset);
  }

  /**
   * 推流心跳
   * @param uId
   * @param sk
   * @param seq_no
   * @returns {ArrayBuffer}
   */
  mUrlHeartbeatRequest(uId, sk, seq_no) {
    let body = {
      uId: uId,
      sk: sk,
    };
    let obj = {
      version: 0,
      mark: 1,
      pt: 0,
      x: 0,
      reserved: 0,
      seq_no: seq_no,
      timestamp: new Date().getTime(),
      id: 1019,
    };
    // 创建一个缓冲区来存储二进制数据
    const buffer = new ArrayBuffer(1024); // 分配足够大的空间
    const view = new DataView(buffer);
    let offset = 0;

    // 按照字段顺序写入二进制数据
    // version: 假设是1字节无符号整数

    let version = (obj.version << 6) | (obj.marker << 5) | obj.pt;

    view.setUint8(offset, version);
    offset += 1;

    // reserved: 假设是1字节无符号整数
    view.setUint8(offset, obj.reserved);
    offset += 1;

    // seq_no: 假设是4字节无符号整数
    view.setUint16(offset, obj.seq_no, false); // true表示小端字节序
    offset += 2;

    // timestamp: 假设是4字节无符号整数
    view.setUint32(offset, obj.timestamp, false);
    offset += 4;

    // id: 假设是2字节无符号整数
    view.setUint32(offset, obj.id, false);
    offset += 4;
    const bodyStr = JSON.stringify(body);
    let length = bodyStr.length;
    // length: 假设是2字节无符号整数
    view.setUint32(offset, length, false);
    offset += 4;

    // body: 将JSON字符串转换为UTF-8编码的二进制数据

    const encoder = new TextEncoder();
    const bodyData = encoder.encode(bodyStr);

    // 将body数据写入缓冲区
    for (let i = 0; i < bodyData.length; i++) {
      view.setUint8(offset, bodyData[i]);
      offset += 1;
    }

    // 返回实际使用的缓冲区部分
    return buffer.slice(0, offset);
  }
}
export default JmuxerMessage;
