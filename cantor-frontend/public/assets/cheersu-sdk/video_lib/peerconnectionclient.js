import EnhancedEventEmitter from "./EnhancedEventEmitter";
import Logger from "./Logger";
// import adapter from "webrtc-adapter";
const logger = new Logger("PeerConnectionClient");

export class PeerConnectionClient extends EnhancedEventEmitter {
  constructor(params, startTime) {
    super(logger);
    this.params_ = params;
    this.startTime_ = startTime || Date.now();
    this.bytesReceived = 0;
    this.lastBytesReceived = 0;
    this.framesDecoded = 0;
    this.lastFramesDecoded = 0;
    logger.debug("Creating RTCPeerConnnection.");
    // console.log(
    //   adapter.browserDetails.browser,
    //   "adapter.browserDetails.browser"
    // );
    // Create an RTCPeerConnection via the polyfill (adapter.js).
    this.pc_ = new RTCPeerConnection(
      {
        bundlePolicy: "max-bundle",
        rtcpMuxPolicy: "require",
        iceServers: this.setIceServers(this.params_.iceServers),
        sdpSemanticsc: "unified-plan",
      },
      {
        optional: [
          // Enable DTLS
          { DtlsSrtpKeyAgreement: true },
          { googDscp: false },
          { googIPv6: false },
        ],
      }
    );

    this.pc_.onicecandidate = this.onIceCandidate.bind(this);
    this.pc_.ontrack = this.onRemoteStreamAdded.bind(this);
    this.pc_.onremovestream = logger.debug.bind(null, "Remote stream removed.");

    //  signalingState 的值发生改变时，该事件被触发
    this.pc_.onsignalingstatechange = this.onSignalingStateChanged.bind(this);

    //  iceConnectionState 改变时，这个事件被触发
    this.pc_.oniceconnectionstatechange =
      this.onIceConnectionStateChanged.bind(this);
    this.pc_.onconnectionstatechange = this.onConnectionStateChange.bind(this);

    this.datachannel_ = undefined;

    this.onerror = null;
    this.onicedisconnect = null;
    this.onnewicecandidate = null;
    this.onremotehangup = null;
    this.onremotesdpset = null;
    this.onremotestreamadded = null;
    this.onsignalingmessage = null;

    this.pc_.onicegatheringstatechange = (event) => {
      if (this.pc_.iceGatheringState === "failed") {
        // ICE 收集失败的处理逻辑
        this.safeEmit("on-peer-error-status", {
          type: "iceGatheringState",
          status: this.pc_.iceGatheringState,
          message: "ICE 收集失败",
        });
      }
    };
    this.pc_.onicecandidateerror = (event) => {
      console.error("ICE candidate error:", event, event.error);
      // ICE 候选者发送失败的处理逻辑
      this.safeEmit("on-peer-error-status", {
        type: "icecandidate",
        status: event.error,
        message: "ICE 候选者发送失败",
      });
    };
  }

  setIceServers(stus) {
    const urls = this.filterIceServers(stus);
    const iceServers = [];
    if (urls && urls.length) {
      iceServers.push({
        urls: urls,
        username: "cstreaming",
        credential: "cstreaming",
      });
    }
    return iceServers;
  }
  // 过滤掉无效信息
  filterIceServers(stus) {
    if (stus && stus.length) {
      return stus.filter((x) => x.indexOf("127.0.0.1") === -1);
    }
    return [];
  }
  addTrack(track) {
    if (this.pc_ !== undefined) {
      this.pc_.addTrack(track);
    }
  }
  addTransceiver(kind, init) {
    if (this.pc_ !== undefined) {
      this.pc_.addTransceiver(kind, init);
    }
  }
  getTransceivers() {
    if (this.pc_ !== undefined) {
      return this.pc_.getTransceivers();
    } else {
      return undefined;
    }
  }

  createOffer(offerOptions) {
    if (this.pc_ === undefined) {
      return false;
    }

    logger.debug("Sending offer to peer, with constraints: \n");
    return this.pc_.createOffer(offerOptions);
  }

  close() {
    if (this.pc_ === undefined) {
      return;
    }

    this.pc_.close();
    window.dispatchEvent(
      new CustomEvent("pcclosed", {
        detail: {
          pc: this,
          time: new Date(),
        },
      })
    );

    this.pc_ = undefined;
  }
  getPeerConnectionStates() {
    if (this.pc_ === undefined) {
      return undefined;
    }
    let data = {
      signalingState: this.pc_.signalingState,
      iceGatheringState: this.pc_.iceGatheringState,
      iceConnectionState: this.pc_.iceConnectionState,
    };
    this.safeEmit("on-peer-error-status", data);
    logger.debug("PeerConnectionStates ---> " + JSON.stringify(data));
    return data;
  }

  // getPeerConnectionStats(callback) {
  //   if (this.pc_ !== undefined) {
  //     this.pc_.getStats(null).then(callback);
  //   }
  // }
  // 获取帧率
  _getPeerConnectionStats() {
    if (this.pc_ !== undefined) {
      this.pc_.getStats(null).then((stats) => {
        stats.forEach((report) => {
          if (report.type === "inbound-rtp") {
            if (report.mediaType === "video") {
              this.lastBytesReceived = this.bytesReceived;
              this.bytesReceived = report.bytesReceived;
              this.lastFramesDecoded = this.framesDecoded;
              this.framesDecoded = report.framesDecoded;
            }
          }
        });
      });
    }
  }
  getReportInfo() {
    return {
      bytesReceived: this.bytesReceived - this.lastBytesReceived,
      framesDecoded: this.framesDecoded - this.lastFramesDecoded,
    };
  }
  createDataChannel(label, options) {
    if (label === undefined || label === "") {
      logger.debug("You must input label when createDataChannel");
      return;
    }

    if (options !== undefined) {
      this.datachannel_ = this.pc_.createDataChannel(label, options);
    } else {
      this.datachannel_ = this.pc_.createDataChannel(label);
    }
    return this.datachannel_;
  }
  setLocalDescription(sessionDescription) {
    return new Promise((resolve, reject) => {
      if (this.pc_ != undefined) {
        this.pc_.setLocalDescription(sessionDescription);
        resolve(sessionDescription);
      } else {
        reject("Invalid peerconnection!");
      }
    });
  }

  setRemoteDescription(message) {
    logger.debug("set remote sdp======" + message.sdp);

    if (this.pc_ !== undefined) {
      return this.pc_.setRemoteDescription(new RTCSessionDescription(message));
    } else {
      // do nothing.
    }
  }

  setCandidate(message) {
    var candidate = new RTCIceCandidate({
      sdpMLineIndex: message.sdpMLineIndex,
      sdpMid: message.sdpMid,
      candidate: message.sdp,
    });
    //this.recordIceCandidate('Remote', candidate);
    this.pc_
      .addIceCandidate(candidate)
      .then(() => {
        logger.debug("Remote candidate added successfully.");
      })
      .catch(() => {
        this.onError("addIceCandidate");
      });
  }
  onSetRemoteDescriptionSuccess() {
    logger.debug("Set remote session description success.");
    // By now all onaddstream events for the setRemoteDescription have fired,
    // so we can know if the peer has any remote video streams that we need
    // to wait for. Otherwise, transition immediately to the active state.
    var remoteStreams = this.pc_.getRemoteStreams();
    if (this.onremotesdpset) {
      this.onremotesdpset(
        remoteStreams.length > 0 && remoteStreams[0].getVideoTracks().length > 0
      );
    }
  }

  onIceCandidate(event) {
    if (event.candidate) {
      // Eat undesired candidates.
      logger.debug("onIceCandidate=========:" + event.candidate.candidate);
      this.startTime_ = Date.now();
      if (this.filterIceCandidate(event.candidate)) {
        var message = {
          type: "candidate",
          sdpMLineIndex: event.candidate.sdpMLineIndex,
          sdpMid: event.candidate.sdpMid,
          candidate: event.candidate.candidate,
        };
        if (this.onsignalingmessage) {
          this.onsignalingmessage(message, message.type);
        }
        this.recordIceCandidate("Local", event.candidate);
      }
    } else {
      logger.debug("End of candidates.");
    }
  }

  onSignalingStateChanged() {
    if (this.pc_ === undefined) {
      return;
    }
    console.log("Signaling state changed to: " + this.pc_.signalingState);

    if (this.onsignalingstatechange) {
      this.onsignalingstatechange();
    }
  }

  onConnectionStateChange() {
    logger.debug("connection state changed to: " + this.pc_.connectionState);
    if (this.pc_.connectionState === "failed") {
      this.safeEmit("on-peer-error-status", {
        type: "connection",
        status: this.pc_.connectionState,
        message: "connection连接失败",
      });
    }
  }

  onIceConnectionStateChanged() {
    if (this.pc_ === undefined) {
      return;
    }
    logger.debug(
      "ICE connection state changed to: " + this.pc_.iceConnectionState
    );
    if (this.pc_.iceConnectionState === "failed") {
      this.safeEmit("on-peer-error-status", {
        type: "iceConnection",
        status: this.pc_.iceConnectionState,
        message: "ICEConnection连接失败",
      });
    }

    if (
      this.pc_.iceConnectionState === "completed" ||
      this.pc_.iceConnectionState === "connected"
    ) {
      logger.debug(
        "ICE complete time: " +
          (Date.now() - this.startTime_).toFixed(0) +
          "ms."
      );
      this.safeEmit("on-ice-success");
      // peer-connection-connected
    }

    if (
      this.pc_.iceConnectionState === "disconnected" &&
      this.onicedisconnect !== null
    ) {
      this.onicedisconnect();
    }
  }

  // Return false if the candidate should be dropped, true if not.
  filterIceCandidate(candidateObj) {
    var candidateStr = candidateObj.candidate;

    // Always eat TCP candidates. Not needed in this context.
    if (candidateStr.indexOf("tcp") !== -1) {
      return false;
    }

    // If we're trying to eat non-relay candidates, do that.
    /*
    if (this.params_.peerConnectionConfig.iceTransports === 'relay' &&
      iceCandidateType(candidateStr) !== 'relay') {
      return false;
    }
    */

    return true;
  }

  recordIceCandidate(location, candidateObj) {
    if (this.onnewicecandidate) {
      this.onnewicecandidate(location, candidateObj.candidate);
    }
  }

  onRemoteStreamAdded(event) {
    logger.debug("onRemoteStreamAdded.......1");
    if (this.onremotestreamadded) {
      logger.debug("onRemoteStreamAdded.......2");
      this.onremotestreamadded(event.streams[0], event.transceiver);
    }
  }

  onError(tag, error) {
    if (this.onerror) {
      this.onerror(tag + ": " + error.toString());
    }
  }
  getIceConnectionState() {
    return this.pc_.iceConnectionState;
  }
}
