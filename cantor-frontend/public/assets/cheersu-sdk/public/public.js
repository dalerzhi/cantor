function signature(map, ak, sk) {
  return new Promise((resolve, reject) => {
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.floor(Math.random() * 1000);
    const paramsMap = {};
    paramsMap["appId"] = ak;
    paramsMap["data"] = JSON.stringify(map);
    paramsMap["nonce"] = nonce;
    paramsMap["timestamp"] = timestamp;

    const plainStr = Object.entries(paramsMap)
      .map(([key, value]) => `${key}=${value}`)
      .join("&");
    const secretKeySpec = new TextEncoder().encode(sk);
    const encoder = new TextEncoder();
    const data = encoder.encode(plainStr);
    crypto.subtle
      .importKey("raw", secretKeySpec, { name: "HMAC", hash: "SHA-1" }, false, [
        "sign",
      ])
      .then((cryptoKey) => {
        return crypto.subtle.sign("HMAC", cryptoKey, data);
      })
      .then((signatureBuffer) => {
        let signature = btoa(
          String.fromCharCode(...new Uint8Array(signatureBuffer))
        );
        paramsMap["signature"] = signature;
        resolve(paramsMap);
      })
      .catch((err) => {
        reject(err);
      });
  });
}

export { signature };
