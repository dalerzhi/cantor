class BlockQueueBuffer {
  constructor() {
    this.chunks = []; // 保存原始数据块（Uint8Array）
    this.currentPos = 0; // 当前读取位置（相对于第一个块的偏移量）
  }

  /**
   * 追加数据块（不复制，仅引用）
   * @param {Uint8Array} chunk 新数据块
   */
  append(chunk) {
    //console.log("before append :", this.chunks);
    //console.log("append chunk:", chunk);
    this.chunks.push(chunk);
    //console.log("after append :", this.chunks);
  }
  /**
   * 读取指定长度的数据（按需合并块）
   * @param {number} length 需要读取的字节数
   * @returns {Uint8Array} 连续的字节数据
   */
  read(length) {
    const totalBytes = this.getTotalBytes("readFn");
    if (length > totalBytes) {
      throw new Error("Insufficient data");
    }

    const result = new Uint8Array(length);
    let bytesRead = 0;
    //let currentChunkIndex = 0;

    //console.log(totalBytes, bytesRead, length, "totalBytes, bytesRead,length");
    while (bytesRead < length) {
      let chunk = this.chunks[0];
      const remainingInChunk = chunk.byteLength - this.currentPos;
      const bytesToCopy = Math.min(remainingInChunk, length - bytesRead);
      const tempUint8Arr = new Uint8Array(chunk, this.currentPos, bytesToCopy);
      // 复制数据到结果数组
      result.set(tempUint8Arr, bytesRead);

      bytesRead += bytesToCopy;
      this.currentPos += bytesToCopy;

      // 移动到下一个块
      if (this.currentPos >= chunk.byteLength) {
        this.chunks.shift();
        this.currentPos = 0;
        chunk = null;
        //currentChunkIndex++;
      }
      //console.log(this.chunks, "read after this.chunks");
    }
    return result;
  }

  getTotalBytes(type) {
    // console.log(type + " getTotalBytes this.chunks ", this.chunks);
    const total =
      this.chunks.reduce((sum, chunk) => sum + chunk.byteLength, 0) -
      this.currentPos;
    // console.log(type + " getTotalBytes this.chunks total :", total);
    return total;
  }
}

export default BlockQueueBuffer;
