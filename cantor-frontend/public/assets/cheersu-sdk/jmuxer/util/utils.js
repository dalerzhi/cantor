export function appendByteArray(buffer1, buffer2) {
  let tmp = new Uint8Array((buffer1.byteLength | 0) + (buffer2.byteLength | 0));
  tmp.set(buffer1, 0);
  tmp.set(buffer2, buffer1.byteLength | 0);
  return tmp;
}

export function appendFrame(buffer1, frame) {
  //console.log("buffer1 size:",  buffer1.byteLength|0);
  let tmp = new Uint8Array((buffer1.byteLength | 0) + (frame.frameSize | 0));
  tmp.set(buffer1, 0);
  let offset = buffer1.byteLength | 0;
  for (let i = 0; i < frame.packets.length; ++i) {
    tmp.set(frame.packets[i].payload, offset);
    offset += frame.packets[i].hdr.length;
  }

  //console.log(buffer1,  tmp, "appendframe end");

  return tmp;
}

export function appendFrame2(frame) {
  //console.log("buffer1 size:",  buffer1.byteLength|0);
  let tmp = new Uint8Array((frame.frameSize - 4) | 0);
  let offset = 0;
  for (let i = 0; i < frame.packets.length; ++i) {
    if (i === 0) {
      let payloadlength = frame.packets[i].hdr.length - 4;
      const tempUint8Arr = frame.packets[i].payload.subarray(4);
      tmp.set(tempUint8Arr, offset);
      offset += payloadlength;
    } else {
      tmp.set(frame.packets[i].payload, offset);
      offset += frame.packets[i].hdr.length;
    }
  }

  //console.log(buffer1,  tmp, "appendframe end");

  return tmp;
}

export function secToTime(sec) {
  let seconds,
    hours,
    minutes,
    result = "";

  seconds = Math.floor(sec);
  hours = parseInt(seconds / 3600, 10) % 24;
  minutes = parseInt(seconds / 60, 10) % 60;
  seconds = seconds < 0 ? 0 : seconds % 60;

  if (hours > 0) {
    result += (hours < 10 ? "0" + hours : hours) + ":";
  }
  result +=
    (minutes < 10 ? "0" + minutes : minutes) +
    ":" +
    (seconds < 10 ? "0" + seconds : seconds);
  return result;
}
