class PacketBuffer {
  constructor() {
    this.expectedSeq = null; // 下一个期待的序列号
    this.currentPackets = []; // 当前帧的包列表 {hdr, data}
    this.frameSize = 0;
  }

  /**
   * 添加数据包并处理组帧逻辑
   * @param {Object} hdr 协议头（必须包含 seq_no 和 mark 字段）
   * @param {Uint8Array} data 有效载荷数据
   * @param {Function} onFrame 帧完成回调 (hdrArray, mergedData) => void
   * @param {Function} onError 错误回调 (Error) => void
   */
  addPacket(hdr, payload, onFrame, onError) {
    const seq = hdr.seq_no;
    const mark = hdr.mark;

    // 初始化或继续组帧
    if (this.expectedSeq === null) {
      this.expectedSeq = seq;
    }
    if (seq !== this.expectedSeq) {
      console.log(
        "hdr uis " + hdr.id.streamid,
        "seq: " + seq,
        "expectedSeq: " + this.expectedSeq
      );
      throw new Error(
        `hdr uis ${hdr.id.streamid}, hdr ws ${hdr.wsUrl} Sequence discontinuity. Expected ${this.expectedSeq}, got ${seq}`
      );
    }
    this.currentPackets.push({
      hdr,
      payload,
    });
    this.frameSize += hdr.length;
    if (seq === 65535) {
      this.expectedSeq = 0;
    } else {
      this.expectedSeq = seq + 1;
    }
    //console.log(this.expectedSeq, "addPacket")

    // 处理帧完成
    if (mark === 1) {
      onFrame({
        packets: this.currentPackets,
        frameSize: this.frameSize,
      });
      this.currentPackets = []; // 清空当前帧但保持 expectedSeq
      this.frameSize = 0;
    }
  }

  /**
   * 重置缓冲区到初始状态
   */
  clear() {
    this.expectedSeq = null;
    this.currentPackets = [];
  }
}

export default PacketBuffer;
