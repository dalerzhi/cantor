/*
 *  Copyright (c) 2014 The WebRTC project authors. All Rights Reserved.
 *
 *  Use of this source code is governed by a BSD-style license
 *  that can be found in the LICENSE file in the root of the source
 *  tree.
 */

/* More information about these options at jshint.com/docs/options */

import { trace } from "./util";

export function mergeConstraints(cons1, cons2) {
  if (!cons1 || !cons2) {
    return cons1 || cons2;
  }
  var merged = cons1;
  for (var key in cons2) {
    merged[key] = cons2[key];
  }
  return merged;
}

function iceCandidateType(candidateStr) {
  return candidateStr.split(" ")[7];
}

export function maybeSetOpusOptions(sdp, params) {
  // Set Opus in Stereo, if stereo is true, unset it, if stereo is false, and
  // do nothing if otherwise.
  if (params.opusStereo === "true") {
    sdp = setCodecParam(sdp, "opus/48000", "stereo", "1");
  } else if (params.opusStereo === "false") {
    sdp = removeCodecParam(sdp, "opus/48000", "stereo");
  }

  // Set Opus FEC, if opusfec is true, unset it, if opusfec is false, and
  // do nothing if otherwise.
  if (params.opusFec === "true") {
    sdp = setCodecParam(sdp, "opus/48000", "useinbandfec", "1");
  } else if (params.opusFec === "false") {
    sdp = removeCodecParam(sdp, "opus/48000", "useinbandfec");
  }

  // Set Opus DTX, if opusdtx is true, unset it, if opusdtx is false, and
  // do nothing if otherwise.
  if (params.opusDtx === "true") {
    sdp = setCodecParam(sdp, "opus/48000", "usedtx", "1");
  } else if (params.opusDtx === "false") {
    sdp = removeCodecParam(sdp, "opus/48000", "usedtx");
  }

  // Set Opus maxplaybackrate, if requested.
  if (params.opusMaxPbr) {
    sdp = setCodecParam(
      sdp,
      "opus/48000",
      "maxplaybackrate",
      params.opusMaxPbr
    );
  }
  return sdp;
}

export function maybeSetVideoOption(sdp, params) {
  var sdpLines = sdp.split("\r\n");

  if (params.vp8 === false) {
    sdpLines = removeCodecByName(sdpLines, "VP8/90000");
  }
  if (params.vp9 === false) {
    sdpLines = removeCodecByName(sdpLines, "VP9/90000");
  }

  var sdp_new = sdpLines.join("\r\n");
  return sdp_new;
}

export function maybeSetAudioSendBitRate(sdp, params) {
  if (!params.audioSendBitrate) {
    return sdp;
  }
  trace("Prefer audio send bitrate: " + params.audioSendBitrate);
  return preferBitRate(sdp, params.audioSendBitrate, "audio");
}

export function maybeSetAudioReceiveBitRate(sdp, params) {
  if (!params.audioRecvBitrate) {
    return sdp;
  }
  trace("Prefer audio receive bitrate: " + params.audioRecvBitrate);
  return preferBitRate(sdp, params.audioRecvBitrate, "audio");
}

export function maybeSetVideoSendBitRate(sdp, params) {
  if (!params.videoSendBitrate) {
    return sdp;
  }
  trace("Prefer video send bitrate: " + params.videoSendBitrate);
  return preferBitRate(sdp, params.videoSendBitrate, "video");
}

export function maybeSetVideoReceiveBitRate(sdp, params) {
  if (!params.videoRecvBitrate) {
    return sdp;
  }
  trace("Prefer video receive bitrate: " + params.videoRecvBitrate);
  return preferBitRate(sdp, params.videoRecvBitrate, "video");
}

// Add a b=AS:bitrate line to the m=mediaType section.
function preferBitRate(sdp, bitrate, mediaType) {
  var sdpLines = sdp.split("\r\n");

  // Find m line for the given mediaType.
  var mLineIndex = findLine(sdpLines, "m=", mediaType);
  if (mLineIndex === null) {
    trace("Failed to add bandwidth line to sdp, as no m-line found");
    return sdp;
  }

  // Find next m-line if any.
  var nextMLineIndex = findLineInRange(sdpLines, mLineIndex + 1, -1, "m=");
  if (nextMLineIndex === null) {
    nextMLineIndex = sdpLines.length;
  }

  // Find c-line corresponding to the m-line.
  var cLineIndex = findLineInRange(
    sdpLines,
    mLineIndex + 1,
    nextMLineIndex,
    "c="
  );
  if (cLineIndex === null) {
    trace("Failed to add bandwidth line to sdp, as no c-line found");
    return sdp;
  }

  // Check if bandwidth line already exists between c-line and next m-line.
  var bLineIndex = findLineInRange(
    sdpLines,
    cLineIndex + 1,
    nextMLineIndex,
    "b=AS"
  );
  if (bLineIndex) {
    sdpLines.splice(bLineIndex, 1);
  }

  // Create the b (bandwidth) sdp line.
  var bwLine = "b=AS:" + bitrate;
  // As per RFC 4566, the b line should follow after c-line.
  sdpLines.splice(cLineIndex + 1, 0, bwLine);
  sdp = sdpLines.join("\r\n");
  return sdp;
}

// Add an a=fmtp: x-google-min-bitrate=kbps line, if videoSendInitialBitrate
// is specified. We'll also add a x-google-min-bitrate value, since the max
// must be >= the min.
export function maybeSetVideoSendInitialBitRate(sdp, params) {
  var initialBitrate = parseInt(params.videoSendInitialBitrate);
  if (!initialBitrate) {
    return sdp;
  }

  // Validate the initial bitrate value.
  var maxBitrate = parseInt(initialBitrate);
  var bitrate = parseInt(params.videoSendBitrate);
  if (bitrate) {
    if (initialBitrate > bitrate) {
      trace("Clamping initial bitrate to max bitrate of " + bitrate + " kbps.");
      initialBitrate = bitrate;
      params.videoSendInitialBitrate = initialBitrate;
    }
    maxBitrate = bitrate;
  }

  var sdpLines = sdp.split("\r\n");

  // Search for m line.
  var mLineIndex = findLine(sdpLines, "m=", "video");
  if (mLineIndex === null) {
    trace("Failed to find video m-line");
    return sdp;
  }
  // Figure out the first codec payload type on the m=video SDP line.
  var videoMLine = sdpLines[mLineIndex];
  var pattern = new RegExp("m=video\\s\\d+\\s[A-Z/]+\\s");
  var sendPayloadType = videoMLine.split(pattern)[1].split(" ")[0];
  var fmtpLine = sdpLines[findLine(sdpLines, "a=rtpmap", sendPayloadType)];
  var codecName = fmtpLine
    .split("a=rtpmap:" + sendPayloadType)[1]
    .split("/")[0];

  // Use codec from params if specified via URL param, otherwise use from SDP.
  var codec = params.videoSendCodec || codecName;
  sdp = setCodecParam(
    sdp,
    codec,
    "x-google-min-bitrate",
    params.videoSendInitialBitrate.toString()
  );
  sdp = setCodecParam(
    sdp,
    codec,
    "x-google-max-bitrate",
    maxBitrate.toString()
  );

  return sdp;
}

function removePayloadTypeFromMline(mLine, payloadType) {
  mLine = mLine.split(" ");
  for (var i = 0; i < mLine.length; ++i) {
    if (mLine[i] === payloadType.toString()) {
      mLine.splice(i, 1);
    }
  }
  return mLine.join(" ");
}

function removeCodecByName(sdpLines, codec) {
  var index = findLine(sdpLines, "a=rtpmap", codec);
  if (index === null) {
    return sdpLines;
  }
  var payloadType = getCodecPayloadTypeFromLine(sdpLines[index]);
  sdpLines.splice(index, 1);

  // Search for the video m= line and remove the codec.
  var mLineIndex = findLine(sdpLines, "m=", "video");
  if (mLineIndex === null) {
    return sdpLines;
  }
  sdpLines[mLineIndex] = removePayloadTypeFromMline(
    sdpLines[mLineIndex],
    payloadType
  );
  return sdpLines;
}

function removeCodecByPayloadType(sdpLines, payloadType) {
  var index = findLine(sdpLines, "a=rtpmap", payloadType.toString());
  if (index === null) {
    return sdpLines;
  }
  sdpLines.splice(index, 1);

  // Search for the video m= line and remove the codec.
  var mLineIndex = findLine(sdpLines, "m=", "video");
  if (mLineIndex === null) {
    return sdpLines;
  }
  sdpLines[mLineIndex] = removePayloadTypeFromMline(
    sdpLines[mLineIndex],
    payloadType
  );
  return sdpLines;
}

export function maybeRemoveVideoFec(sdp, params) {
  if (params.videoFec !== "false") {
    return sdp;
  }

  var sdpLines = sdp.split("\r\n");

  var index = findLine(sdpLines, "a=rtpmap", "red");
  if (index === null) {
    return sdp;
  }
  var redPayloadType = getCodecPayloadTypeFromLine(sdpLines[index]);
  sdpLines = removeCodecByPayloadType(sdpLines, redPayloadType);

  sdpLines = removeCodecByName(sdpLines, "ulpfec");

  // Remove fmtp lines associated with red codec.
  index = findLine(sdpLines, "a=fmtp", redPayloadType.toString());
  if (index === null) {
    return sdp;
  }
  var fmtpLine = parseFmtpLine(sdpLines[index]);
  var rtxPayloadType = fmtpLine.pt;
  if (rtxPayloadType === null) {
    return sdp;
  }
  sdpLines.splice(index, 1);

  sdpLines = removeCodecByPayloadType(sdpLines, rtxPayloadType);
  return sdpLines.join("\r\n");
}

// Promotes |audioSendCodec| to be the first in the m=audio line, if set.
export function maybePreferAudioSendCodec(sdp, params) {
  return maybePreferCodec(sdp, "audio", "send", params.audioSendCodec);
}

// Promotes |audioRecvCodec| to be the first in the m=audio line, if set.
export function maybePreferAudioReceiveCodec(sdp, params) {
  return maybePreferCodec(sdp, "audio", "receive", params.audioRecvCodec);
}

// Promotes |videoSendCodec| to be the first in the m=audio line, if set.
export function maybePreferVideoSendCodec(sdp, params) {
  return maybePreferCodec(sdp, "video", "send", params.videoSendCodec);
}

// Promotes |videoRecvCodec| to be the first in the m=audio line, if set.
export function maybePreferVideoReceiveCodec(sdp, params) {
  return maybePreferCodec(sdp, "video", "receive", params.videoRecvCodec);
}

// Sets |codec| as the default |type| codec if it's present.
// The format of |codec| is 'NAME/RATE', e.g. 'opus/48000'.
function maybePreferCodec(sdp, type, dir, codec) {
  var str = type + " " + dir + " codec";
  if (!codec) {
    trace("No preference on " + str + ".");
    return sdp;
  }

  trace("Prefer " + str + ": " + codec);

  var sdpLines = sdp.split("\r\n");

  // Search for m line.
  var mLineIndex = findLine(sdpLines, "m=", type);
  if (mLineIndex === null) {
    return sdp;
  }

  // If the codec is available, set it as the default in m line.
  var payload = null;
  // Iterate through rtpmap enumerations to find all matching codec entries
  for (var i = sdpLines.length - 1; i >= 0; --i) {
    // Finds first match in rtpmap
    var index = findLineInRange(sdpLines, i, 0, "a=rtpmap", codec, "desc");
    if (index !== null) {
      // Skip all of the entries between i and index match
      i = index;
      payload = getCodecPayloadTypeFromLine(sdpLines[index]);
      if (payload) {
        // Move codec to top
        sdpLines[mLineIndex] = setDefaultCodec(sdpLines[mLineIndex], payload);
      }
    } else {
      // No match means we can break the loop
      break;
    }
  }

  sdp = sdpLines.join("\r\n");
  return sdp;
}

// Set fmtp param to specific codec in SDP. If param does not exists, add it.
function setCodecParam(sdp, codec, param, value) {
  var sdpLines = sdp.split("\r\n");

  var fmtpLineIndex = findFmtpLine(sdpLines, codec);

  var fmtpObj = {};
  if (fmtpLineIndex === null) {
    var index = findLine(sdpLines, "a=rtpmap", codec);
    if (index === null) {
      return sdp;
    }
    var payload = getCodecPayloadTypeFromLine(sdpLines[index]);
    fmtpObj.pt = payload.toString();
    fmtpObj.params = {};
    fmtpObj.params[param] = value;
    sdpLines.splice(index + 1, 0, writeFmtpLine(fmtpObj));
  } else {
    fmtpObj = parseFmtpLine(sdpLines[fmtpLineIndex]);
    fmtpObj.params[param] = value;
    sdpLines[fmtpLineIndex] = writeFmtpLine(fmtpObj);
  }

  sdp = sdpLines.join("\r\n");
  return sdp;
}

// Remove fmtp param if it exists.
function removeCodecParam(sdp, codec, param) {
  var sdpLines = sdp.split("\r\n");

  var fmtpLineIndex = findFmtpLine(sdpLines, codec);
  if (fmtpLineIndex === null) {
    return sdp;
  }

  var map = parseFmtpLine(sdpLines[fmtpLineIndex]);
  delete map.params[param];

  var newLine = writeFmtpLine(map);
  if (newLine === null) {
    sdpLines.splice(fmtpLineIndex, 1);
  } else {
    sdpLines[fmtpLineIndex] = newLine;
  }

  sdp = sdpLines.join("\r\n");
  return sdp;
}

// Split an fmtp line into an object including 'pt' and 'params'.
function parseFmtpLine(fmtpLine) {
  var fmtpObj = {};
  var spacePos = fmtpLine.indexOf(" ");
  var keyValues = fmtpLine.substring(spacePos + 1).split(";");

  var pattern = new RegExp("a=fmtp:(\\d+)");
  var result = fmtpLine.match(pattern);
  if (result && result.length === 2) {
    fmtpObj.pt = result[1];
  } else {
    return null;
  }

  var params = {};
  for (var i = 0; i < keyValues.length; ++i) {
    var pair = keyValues[i].split("=");
    if (pair.length === 2) {
      params[pair[0]] = pair[1];
    }
  }
  fmtpObj.params = params;

  return fmtpObj;
}

// Generate an fmtp line from an object including 'pt' and 'params'.
function writeFmtpLine(fmtpObj) {
  if (!fmtpObj.hasOwnProperty("pt") || !fmtpObj.hasOwnProperty("params")) {
    return null;
  }
  var pt = fmtpObj.pt;
  var params = fmtpObj.params;
  var keyValues = [];
  var i = 0;
  for (var key in params) {
    keyValues[i] = key + "=" + params[key];
    ++i;
  }
  if (i === 0) {
    return null;
  }
  return "a=fmtp:" + pt.toString() + " " + keyValues.join(";");
}

// Find fmtp attribute for |codec| in |sdpLines|.
function findFmtpLine(sdpLines, codec) {
  // Find payload of codec.
  var payload = getCodecPayloadType(sdpLines, codec);
  // Find the payload in fmtp line.
  return payload ? findLine(sdpLines, "a=fmtp:" + payload.toString()) : null;
}

// Find the line in sdpLines that starts with |prefix|, and, if specified,
// contains |substr| (case-insensitive search).
function findLine(sdpLines, prefix, substr) {
  return findLineInRange(sdpLines, 0, -1, prefix, substr);
}

// Find the line in sdpLines[startLine...endLine - 1] that starts with |prefix|
// and, if specified, contains |substr| (case-insensitive search).
export function findLineInRange(
  sdpLines,
  startLine,
  endLine,
  prefix,
  substr,
  direction
) {
  if (direction === undefined) {
    direction = "asc";
  }

  direction = direction || "asc";

  if (direction === "asc") {
    // Search beginning to end
    var realEndLine = endLine !== -1 ? endLine : sdpLines.length;
    for (var i = startLine; i < realEndLine; ++i) {
      if (sdpLines[i].indexOf(prefix) === 0) {
        if (
          !substr ||
          sdpLines[i].toLowerCase().indexOf(substr.toLowerCase()) !== -1
        ) {
          return i;
        }
      }
    }
  } else {
    // Search end to beginning
    var realStartLine = startLine !== -1 ? startLine : sdpLines.length - 1;
    for (var j = realStartLine; j >= 0; --j) {
      if (sdpLines[j].indexOf(prefix) === 0) {
        if (
          !substr ||
          sdpLines[j].toLowerCase().indexOf(substr.toLowerCase()) !== -1
        ) {
          return j;
        }
      }
    }
  }
  return null;
}

// Gets the codec payload type from sdp lines.
function getCodecPayloadType(sdpLines, codec) {
  var index = findLine(sdpLines, "a=rtpmap", codec);
  return index ? getCodecPayloadTypeFromLine(sdpLines[index]) : null;
}

// Gets the codec payload type from an a=rtpmap:X line.
function getCodecPayloadTypeFromLine(sdpLine) {
  var pattern = new RegExp("a=rtpmap:(\\d+) [a-zA-Z0-9-]+\\/\\d+");
  var result = sdpLine.match(pattern);
  return result && result.length === 2 ? result[1] : null;
}

// Returns a new m= line with the specified codec as the first one.
function setDefaultCodec(mLine, payload) {
  var elements = mLine.split(" ");

  // Just copy the first three parameters; codec order starts on fourth.
  var newLine = elements.slice(0, 3);

  // Put target payload first and copy in the rest.
  newLine.push(payload);
  for (var i = 3; i < elements.length; i++) {
    if (elements[i] !== payload) {
      newLine.push(elements[i]);
    }
  }
  return newLine.join(" ");
}

/* Below are newly added functions */

// Following codecs will not be removed from SDP event they are not in the
// user-specified codec list.
const audioCodecAllowList = ["CN", "telephone-event"];
const videoCodecAllowList = ["red", "ulpfec", "flexfec"];

// Returns a new m= line with the specified codec order.
function setCodecOrder(mLine, payloads) {
  const elements = mLine.split(" ");

  // Just copy the first three parameters; codec order starts on fourth.
  let newLine = elements.slice(0, 3);

  // Concat payload types.
  newLine = newLine.concat(payloads);

  return newLine.join(" ");
}

// Append RTX payloads for existing payloads.
function appendRtxPayloads(sdpLines, payloads) {
  for (const payload of payloads) {
    const index = findLine(sdpLines, "a=fmtp", "apt=" + payload);
    if (index !== null) {
      const fmtpLine = parseFmtpLine(sdpLines[index]);
      payloads.push(fmtpLine.pt);
    }
  }
  return payloads;
}

// Remove a codec with all its associated a lines.
function removeCodecFramALine(sdpLines, payload) {
  const pattern = new RegExp("a=(rtpmap|rtcp-fb|fmtp):" + payload + "\\s");
  for (let i = sdpLines.length - 1; i > 0; i--) {
    if (sdpLines[i].match(pattern)) {
      sdpLines.splice(i, 1);
    }
  }
  return sdpLines;
}

// Reorder codecs in m-line according the order of |codecs|. Remove codecs from
// m-line if it is not present in |codecs|
// The format of |codec| is 'NAME/RATE', e.g. 'opus/48000'.
export function reorderCodecs(sdp, type, codecs) {
  if (!codecs || codecs.length === 0) {
    return sdp;
  }

  codecs =
    type === "audio"
      ? codecs.concat(audioCodecAllowList)
      : codecs.concat(videoCodecAllowList);

  let sdpLines = sdp.split("\r\n");

  // Search for m line.
  const mLineIndex = findLine(sdpLines, "m=", type);
  if (mLineIndex === null) {
    return sdp;
  }

  const originPayloads = sdpLines[mLineIndex].split(" ");
  originPayloads.splice(0, 3);

  // If the codec is available, set it as the default in m line.
  let payloads = [];
  for (const codec of codecs) {
    for (let i = 0; i < sdpLines.length; i++) {
      const index = findLineInRange(sdpLines, i, -1, "a=rtpmap", codec);
      if (index !== null) {
        const payload = getCodecPayloadTypeFromLine(sdpLines[index]);
        if (payload) {
          payloads.push(payload);
          i = index;
        }
      }
    }
  }
  payloads = appendRtxPayloads(sdpLines, payloads);
  sdpLines[mLineIndex] = setCodecOrder(sdpLines[mLineIndex], payloads);

  // Remove a lines.
  for (const payload of originPayloads) {
    if (payloads.indexOf(payload) === -1) {
      sdpLines = removeCodecFramALine(sdpLines, payload);
    }
  }

  sdp = sdpLines.join("\r\n");
  return sdp;
}

// Add legacy simulcast.
export function addLegacySimulcast(sdp, type, numStreams) {
  if (!numStreams || !(numStreams > 1)) {
    return sdp;
  }

  let sdpLines = sdp.split("\r\n");
  // Search for m line.
  const mLineStart = findLine(sdpLines, "m=", type);
  if (mLineStart === null) {
    return sdp;
  }
  let mLineEnd = findLineInRange(sdpLines, mLineStart + 1, -1, "m=");
  if (mLineEnd === null) {
    mLineEnd = sdpLines.length;
  }

  const ssrcGetter = (line) => {
    const parts = line.split(" ");
    const ssrc = parts[0].split(":")[1];
    return ssrc;
  };

  // Process ssrc lines from mLineIndex.
  const removes = new Set();
  const ssrcs = new Set();
  const gssrcs = new Set();
  const simLines = [];
  const simGroupLines = [];
  let i = mLineStart + 1;
  while (i < mLineEnd) {
    const line = sdpLines[i];
    if (line === "") {
      break;
    }
    if (line.indexOf("a=ssrc:") > -1) {
      const ssrc = ssrcGetter(sdpLines[i]);
      ssrcs.add(ssrc);
      if (line.indexOf("cname") > -1 || line.indexOf("msid") > -1) {
        for (let j = 1; j < numStreams; j++) {
          const nssrc = parseInt(ssrc) + j + "";
          simLines.push(line.replace(ssrc, nssrc));
        }
      } else {
        removes.add(line);
      }
    }
    if (line.indexOf("a=ssrc-group:FID") > -1) {
      const parts = line.split(" ");
      gssrcs.add(parts[2]);
      for (let j = 1; j < numStreams; j++) {
        const nssrc1 = parseInt(parts[1]) + j + "";
        const nssrc2 = parseInt(parts[2]) + j + "";
        simGroupLines.push(
          line.replace(parts[1], nssrc1).replace(parts[2], nssrc2)
        );
      }
    }
    i++;
  }

  const insertPos = i;
  ssrcs.forEach((ssrc) => {
    if (!gssrcs.has(ssrc)) {
      let groupLine = "a=ssrc-group:SIM";
      groupLine = groupLine + " " + ssrc;
      for (let j = 1; j < numStreams; j++) {
        groupLine = groupLine + " " + (parseInt(ssrc) + j);
      }
      simGroupLines.push(groupLine);
    }
  });

  simLines.sort();
  // Insert simulcast ssrc lines.
  sdpLines.splice(insertPos, 0, ...simGroupLines);
  sdpLines.splice(insertPos, 0, ...simLines);
  sdpLines = sdpLines.filter((line) => !removes.has(line));

  sdp = sdpLines.join("\r\n");
  return sdp;
}

export function setBitrate(sdp, encodingParametersList) {
  var sdpLines = sdp.split("\r\n");

  for (const encodingParameters of encodingParametersList) {
    if (encodingParameters.codec_name != undefined) {
      var mLineIndex = findLineInRange(sdpLines, 0, -1, "m=video");
      if (mLineIndex === null) {
        trace("Failed to setBitrate to sdp, as no video found");
        break;
      }

      var over = false;
      while (!over) {
        // Find next m-line if any.
        var nextMLineIndex = findLineInRange(
          sdpLines,
          mLineIndex + 1,
          -1,
          "a=rtpmap",
          encodingParameters.codec_name
        );
        if (nextMLineIndex === null) {
          break;
        }

        var fmtpObj = {};

        var payload = getCodecPayloadTypeFromLine(sdpLines[nextMLineIndex]);

        var fmtpLineIndex = findLineInRange(
          sdpLines,
          mLineIndex + 1,
          -1,
          "a=fmtp:" + payload.toString()
        );
        if (fmtpLineIndex === null) {
          fmtpObj.pt = payload.toString();
          fmtpObj.params = {};
          fmtpObj.params[encodingParameters.max_bitrate_key] =
            encodingParameters.max_bitrate_value;
          fmtpObj.params[encodingParameters.min_bitrate_key] =
            encodingParameters.min_bitrate_value;
          fmtpObj.params[encodingParameters.start_bitrate_key] =
            encodingParameters.start_bitrate_value;
          sdpLines.splice(nextMLineIndex + 1, 0, writeFmtpLine(fmtpObj));
        } else {
          fmtpObj = parseFmtpLine(sdpLines[fmtpLineIndex]);
          fmtpObj.params[encodingParameters.max_bitrate_key] =
            encodingParameters.max_bitrate_value;
          fmtpObj.params[encodingParameters.min_bitrate_key] =
            encodingParameters.min_bitrate_value;
          fmtpObj.params[encodingParameters.start_bitrate_key] =
            encodingParameters.start_bitrate_value;
          sdpLines[fmtpLineIndex] = writeFmtpLine(fmtpObj);
        }
        mLineIndex = nextMLineIndex;
      }
    }
  }

  sdp = sdpLines.join("\r\n");
  return sdp;
}

export function setAudioNack(sdp) {
  var sdpLines = sdp.split("\r\n");
  // SDPs sent from MCU use \n as line break.
  if (sdpLines.length <= 1) {
    sdpLines = sdp.split("\n");
  }
  var fmtpLineIndex = findFmtpLine(sdpLines, "opus/48000");
  if (fmtpLineIndex) {
    var index = findLine(sdpLines, "a=rtpmap", "opus/48000");
    if (index === null) {
      return sdp;
    }
    var payload = getCodecPayloadTypeFromLine(sdpLines[index]);
    sdpLines.splice(
      fmtpLineIndex,
      0,
      "a=rtcp-fb:" + payload.toString() + " " + "nack"
    );
  }
  return sdpLines.join("\r\n");
}
