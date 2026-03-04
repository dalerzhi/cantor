// import { ZstdInit } from "@oneidentity/zstd-js";
const pro = true;
// import * as fzstd from "fzstd";
// 默认为1.0.51及以上版本支持，但现在还未部署。
const minVersionNumbers = [1, 0, 51];
//压缩
export function ZstdBrowser(noticeRequest, version) {
  // noticeRequest = noticeRequest + key
  return new Promise((resolve, reject) => {
    if (pro) resolve(noticeRequest);
    if (!getKeyCodeToVersion(version)) resolve(noticeRequest);
    // 如果不存在，返回
    if (!noticeRequest) return resolve(noticeRequest);
    // 如果小于1024字节，返回
    if (noticeRequest.length < 1024) resolve(noticeRequest);
    // 将传入的字符串编码为 UTF-8 格式的字节序列
    // const data =
    //   typeof noticeRequest === "string"
    //     ? new TextEncoder().encode(noticeRequest)
    //     : noticeRequest;
    // ZstdInit()
    //   .then(({ ZstdSimple }) => {
    //     // You can use the library from now
    //     const encodded = ZstdSimple.compress(data, 3);
    //     // 将utf-8反解为base64字符串
    //     const b = String.fromCharCode(...Array.from(encodded));
    //     const text = btoa(b);
    //     resolve(text);
    //   })
    //   .catch((err) => {
    //     reject("压缩失败", err);
    //   });
  });
}

// 解压
export function ZstdDecompress(base64String, version) {
  return new Promise((resolve, reject) => {
    try {
      if (pro) resolve(base64String);
      if (!getKeyCodeToVersion(version)) resolve(base64String);
      // 将 Base64 字符串解码为二进制字符串
      // const binaryString = atob(base64String);
      //
      // // 将二进制字符串转换为 Uint8Array
      // const compressed = new Uint8Array(binaryString.length);
      // for (let i = 0; i < binaryString.length; i++) {
      //   compressed[i] = binaryString.charCodeAt(i);
      // }
      //
      // // 解压数据
      // const decompressed = fzstd.decompress(compressed);
      //
      // // 将解压后的字节数组转换回字符串
      // const decoder = new TextDecoder();
      // const originalString = decoder.decode(decompressed);
      //
      // resolve(originalString);
    } catch (err) {
      reject("解压或解码失败", err);
    }
  });
}
/**
 * 根据版本号判断是否支持压缩和解压
 * @returns {boolean}
 */
function getKeyCodeToVersion(versionStr) {
  if (versionStr) {
    let version = versionStr.split(".");
    if (version && version.length > 3) {
      const [first, second, third] = version;
      if (
        Number(first) > minVersionNumbers[0] ||
        (Number(first) >= minVersionNumbers[0] &&
          Number(second) > minVersionNumbers[1]) ||
        (Number(first) >= minVersionNumbers[0] &&
          Number(second) >= minVersionNumbers[1] &&
          Number(third) >= minVersionNumbers[2])
      ) {
        return true;
      }
    }
  }
  return false;
}
