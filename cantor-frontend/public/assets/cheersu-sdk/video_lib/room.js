import { sendAsyncUrlRequest, parseJSON } from "./util";
import EnhancedEventEmitter from "./EnhancedEventEmitter";
import Logger from "./Logger";
import { SignalChannelNative } from "./SignalChannelNative";
import Message from "./message";
import { PeerConnectionClient } from "./peerconnectionclient";
import { Peer } from "./Peer";
import { reorderCodecs } from "./sdputils";

import { UserMedia } from "./UserMedia";
const logger = new Logger("Room");
import { ZstdBrowser, ZstdDecompress } from "./Zstd";
export class Room extends EnhancedEventEmitter {
  constructor(cb, errCb, heartBeatTime = 15000, cstreamingBuildVersion) {
    super(logger);
    this.HEARTBEAT_INTERVAL_MS = heartBeatTime; //20secs
    this.HEARTBEAT_TIMEOUT_TIMES = 3;
    this.cstreamingBuildVersion = cstreamingBuildVersion || "";
    this.params_ = {};
    this.roomID_ = 4455;
    this.channel_ = undefined;
    this.lastTimestamp_ = 0;
    this.msg_ = new Message();
    this.pcclient_ = undefined;
    this.old_pcclient = undefined;
    this.myself_ = undefined;
    this.myLastId_ = undefined;
    this.another_ = undefined;
    this.heartbeatTimer = undefined;
    this.hb_timstamp = 0;
    this.networkInfo = undefined;
    this.option = undefined;
    this.leaveNotifyStstus = false;
    this.PeerConnectionClientTimer = null;
    this.callback = cb;
    this.errCb = errCb;
    this.anotherLeaveNotify = false;
    this.addBase64ImageCss = null;
    this.resetTimer = null;
    this.controlCloudUpStatus = false;
    this.transactionId = "";
    this.isOldMessage = false;
    this.streamVideo = null;
    this.streamAudio = null;
    this.userMedia = null;
    this.maxResolution = {
      maxW: 0,
      maxH: 0,
      idealWidth: 0,
      idealHeight: 0,
    };
    this.timeoutSeconds = 1000 * 60;
    this._mediaConfig = {
      codecName: "H264", // ex: 'H264', 'VP8', 'VP9'
      height: 1920,
      width: 1080,
      frameRate: 60,
      startBitrate: 10000, //10kbps
      minBitrate: 8000, //8kbps
      maxBitrate: 12000, //12kbps
      adptTermResolutionFlag: 0, // 暂时不暴露
      imageQuality: 1, // 画质
      mode: 1, // 模式
      scale: 1.0, // 暂时不暴露
    };
  }

  join(option, serverParams) {
    if (this.myself_ !== undefined) {
      this.myLastId_ = this.myself_.id;
    }
    this.myself_ = new Peer();
    if (option !== undefined) {
      logger.debug("Read to join room.");
      this.option = option;
    } else {
      logger.debug("Read to rejoin room.");
      option = this.option;
    }
    this.setUserMediaConfig(option.locationMediaConfig);
    return new Promise((resolve, reject) => {
      if (option === undefined || option.roomID === undefined) {
        reject("You must support rooid.");
      }
      this._getToken(serverParams)
        .then(() => {
          this.roomID_ = this.params_.roomID;
          this.myself_.setId(this.params_.peerID);
          this.channel_ = new SignalChannelNative(
            this.params_.wssUrl,
            this.params_.wssUrlList,
            this.callback
          );
          this.channel_.on("connection_closed", (event, message) => {
            this._onSignalChannelClosed(event, message);
          });
          // Listen notify
          this.channel_.on("message-notify", (event, message) => {
            this._onMessageNotify(event, message);
          });
          this.channel_.on("fast-reconnect-success", (event, message) => {
            this._onSignalChannelFastReconnectSuccess(event, message);
          });
          this.channel_.on("on-signal-error-status", (message) => {
            // 如果websocket失败，那么room将不会被渲染，则使用监听函数
            this.errCb(message);
          });
          // Register heartbeat timer.
          this.hb_timstamp = this._getNowMS();
          this.heartbeatTimer = setInterval(
            this.sendHeartBeat.bind(this),
            this.HEARTBEAT_INTERVAL_MS
          );
          return this.channel_.open();
        })
        .then(() => {
          var user_join = this.msg_.getUserJoinRequest();
          user_join.req_msg.timestamp = this._getTimestamp();
          user_join.req_msg.roomID = this.roomID_;
          if (this.myLastId_ !== undefined) {
            // rejoin
            user_join.req_msg.lastPeerID = this.myLastId_;
          }
          user_join.req_msg.peerID = this.myself_.id;
          // 设置用户无操作时间
          user_join.req_msg.userConfig.noOperationTime = option.noOperationTime;
          // 设置云机键盘类型
          const terminalType = Number(option.terminalType);
          if ([1, 2].includes(terminalType)) {
            user_join.req_msg.userConfig.termType = option.terminalType;
          }
          // 是否 []
          user_join.req_msg.userConfig.useCimiFlag = [0, 1].includes(
            option.useCimiFlag
          )
            ? option.useCimiFlag
            : 0;

          user_join.req_msg.userConfig.inputMethodType = [1, 2].includes(
            option.inputMethodType
          )
            ? option.inputMethodType
            : 1;
          if (option.mediaConfig !== undefined) {
            user_join.req_msg.mediaConfig.screen.frameRate =
              option.mediaConfig.frameRate;
            // user_join.req_msg.mediaConfig.screen.targetBitrate =
            //   option.mediaConfig.bitrate;
            user_join.req_msg.mediaConfig.screen.startBitrate =
              option.mediaConfig.startBitrate;
            user_join.req_msg.mediaConfig.screen.minBitrate =
              option.mediaConfig.minBitrate;
            user_join.req_msg.mediaConfig.screen.maxBitrate =
              option.mediaConfig.maxBitrate;
            user_join.req_msg.mediaConfig.screen.width = Number(
              option.mediaConfig.resolution.width
            );
            user_join.req_msg.mediaConfig.screen.height = Number(
              option.mediaConfig.resolution.height
            );
            user_join.req_msg.mediaConfig.screen.adptTermResolutionFlag =
              option.mediaConfig.adptTermResolutionFlag || 0;
            user_join.req_msg.mediaConfig.screen.codecName =
              option.mediaConfig.codecName || "H264";
            user_join.req_msg.mediaConfig.screen.imageQuality =
              option.mediaConfig.imageQuality || 1;
            user_join.req_msg.mediaConfig.screen.mode =
              option.mediaConfig.mode || 1;
            user_join.req_msg.mediaConfig.screen.scale =
              option.mediaConfig.scale || 1.0;
          }
          if (option.packageName) {
            user_join.req_msg.startApp = {
              packageName: option.packageName,
            };
          }
          this.channel_.send(user_join, (response) => {
            if (response.result !== "success") {
              reject("Join room failed. reason:" + response.result);
            } else {
              // update the ts
              this.hb_timstamp = this._getNowMS();
              logger.debug("Join success ");
              // Peers
              this._createAnotherPeer(response.anotherPeerID);
              let data = { ...user_join.req_msg.mediaConfig.screen };
              this._setMediaConfig(data);
              resolve(this.another_);
            }
          });
        })
        .catch((error) => {
          reject("Join room error: " + error);
        });
    });
  }
  _setMediaConfig(config) {
    this._mediaConfig = { ...this._mediaConfig, ...config };
  }
  setUserMediaConfig(mediaOption) {
    this.userMedia = new UserMedia(mediaOption.video, mediaOption.audio);
  }
  // 主动离开
  leave(status = true) {
    this.leaveNotifyStstus = status;
    this._closePeerConnectionClient(false);
    // 关闭心跳
    clearInterval(this.heartbeatTimer);
    logger.debug("Send leave room message to server.");
    if (status) {
      let leave_req = this.msg_.getUserLeaveRequest();
      leave_req.req_msg.roomID = this.roomID_;
      leave_req.req_msg.timestamp = this._getTimestamp();
      leave_req.req_msg.peerID = this.myself_.id;
      this.channel_.send(leave_req, (response) => {});
    }
    // Wait for 200ms
    setTimeout(() => {
      this.channel_ && this.channel_.close();
      this.channel_ = undefined;
      this.another_ = undefined;
      logger.debug("bye bye!");
    }, 10);
  }

  getCalc43(w, h) {
    // 按宽算高

    const info = {
      maxW: w,
      maxH: h,
    };
    const h4w = Math.floor((w * 9) / 16);
    if (h4w <= h) {
      info.idealWidth = w;
      info.idealHeight = h4w;
    } else {
      const w4h = Math.floor((h * 16) / 9);
      info.idealWidth = w4h;
      info.idealHeight = h;
    }
    if (info.idealWidth > 1280 && info.idealHeight > 720) {
      info.idealWidth = 1280;
      info.idealHeight = 720;
    }
    return info;
  }

  /**
   * 设置流
   * @param codecName  编码
   * @param enableAudio 音频
   * @param enableVideo  视频
   * @param cameraId  0前置 1后置
   * @returns {Promise<void>}
   */
  async getStream({
    codecName = "H264",
    enableAudio = false,
    enableVideo = false,
    cameraId = 0,
  }) {
    // 如果没有获取最大分辨率
    if (!this.maxResolution.maxW && !this.maxResolution.maxH) {
      const maxInfo = await this.getMaxResolution(cameraId);
      this.maxResolution = this.getCalc43(maxInfo.maxWidth, maxInfo.maxHeight);
    }
    // 切换摄像头，说明老的还在，关闭老的
    if (enableVideo && this.streamVideo) {
      this.streamVideo.getTracks().forEach((t) => t.stop());
      this.streamVideo = null;
      this.safeEmit("on-cloud-media", {
        type: "video",
        status: false,
      });
    }
    // 判断是否授权
    if (enableVideo || enableAudio) {
      if (
        (enableVideo && !this.streamVideo) ||
        (enableAudio && !this.streamAudio)
      ) {
        let deviceId = 0;
        if (enableVideo) {
          // 拿到所有设备
          const devices = await navigator.mediaDevices.enumerateDevices();
          const videoDevs = devices.filter((d) => d.kind === "videoinput");
          if (videoDevs.length === 0) {
            this.safeEmit("on-room-error-status", {
              type: "mediaDevices",
              status: "error",
              code: -1,
              message: "没有找到视频输入设备，请检测是否有视频输入设备.",
            });
            return;
          }
          // 0 取第一个（一般是前置），1 取最后一个（一般是后置）
          const idx = cameraId === 0 ? 0 : videoDevs.length - 1;
          deviceId = videoDevs[idx].deviceId;
        }
        const videoConfig = {
          deviceId: { exact: deviceId },
          width: {
            ideal: this.maxResolution.idealWidth || 1280,
            max: this.maxResolution.maxW || 1280,
          },
          height: {
            ideal: this.maxResolution.idealHeight || 720,
            max: this.maxResolution.maxH || 720,
          },
        };
        navigator.mediaDevices
          .getUserMedia({
            video: enableVideo ? videoConfig : enableVideo, // 请求视频流
            audio: enableAudio, // 请求音频流
          })
          .then((stream) => {
            if (enableVideo) {
              this.streamVideo = stream;
              this.safeEmit("on-cloud-media", {
                type: "video",
                status: true,
              });
            }
            if (enableAudio) {
              this.streamAudio = stream;
              this.safeEmit("on-cloud-media", {
                type: "audio",
                status: true,
              });
            }
            this.publish({ stream, enableAudio, enableVideo, codecName });
          })
          .catch((err) => {
            logger.debug("navigator.mediaDevices.getUserMedia is err", err);
          });
      } else {
        logger.debug(
          "配置项enableVideo为" + enableVideo,
          "配置项enableAudio为" + enableAudio
        );
      }
    }
  }
  // 获取视频流
  publish({ stream = "", enableAudio = false, enableVideo = true, codecName }) {
    // 第一步，判断是输出音频还是视频
    stream
      .getTracks()
      .forEach((track) => this.pcclient_.addTrack(track, stream));
    this.ACENegotiate(codecName);
  }
  async getMaxResolution(deviceIndex = 0) {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter(
        (device) => device.kind === "videoinput"
      );
      console.log(videoDevices, "videoDevices");
      if (videoDevices.length === 0) {
        this.safeEmit("on-room-error-status", {
          type: "mediaDevices",
          status: "error",
          code: -1,
          message: "没有找到视频输入设备，请检测是否有视频输入设备.",
        });
        return;
      }

      let selectedDevice = videoDevices[deviceIndex];
      if (!selectedDevice) {
        selectedDevice = videoDevices[deviceIndex];
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { deviceId: selectedDevice.deviceId },
      });

      const track = stream.getVideoTracks()[0];
      const capabilities = track.getCapabilities();

      const maxWidth =
        capabilities.width && capabilities.width.max
          ? capabilities.width.max
          : null;
      const maxHeight =
        capabilities.height && capabilities.height.max
          ? capabilities.height.max
          : null;

      logger.debug("Max Resolution:", maxWidth, "x", maxHeight);

      stream.getTracks().forEach((track) => track.stop());

      return { maxWidth, maxHeight };
    } catch (error) {
      console.error(
        "Error accessing media devices or getting capabilities:",
        error
      );
    }
  }

  removeTracks(type) {
    if (type === "video" && this.streamVideo) {
      this.streamVideo.getTracks().forEach((track) => track.stop());
      this.streamVideo = null;
      this.safeEmit("on-cloud-media", {
        type: "video",
        status: false,
      });
    }
    if (type === "audio" && this.streamAudio) {
      this.streamAudio.getTracks().forEach((track) => track.stop());
      this.streamAudio = null;
      this.safeEmit("on-cloud-media", {
        type: "audio",
        status: false,
      });
    }
  }
  pull(options) {
    return new Promise((resolve, reject) => {
      var enableAudio = false;
      var enableVideo = false;
      var enableData = false;
      if (options.audio !== undefined && options.audio !== false) {
        enableAudio = true;
      }
      if (options.video !== undefined && options.video !== false) {
        enableVideo = true;
      }
      if (options.data !== undefined && options.data !== false) {
        enableData = true;
      }
      if (!enableAudio && !enableVideo && !enableData) {
        reject("You must enable audio or video at least.");
      }
      this._openPeerConnectionClient();
      this.callback({
        type: "data-channel-create",
        message: "dataChannel开始创建",
      });
      this.another_.setDataChannel(
        this.pcclient_.createDataChannel("touchevent")
      );
      if (enableAudio) {
        this.pcclient_.addTransceiver("audio", { direction: "recvonly" });
      }
      if (enableVideo) {
        this.pcclient_.addTransceiver("video", { direction: "recvonly" });
      }
      this.ACENegotiate(options.codecName, resolve, reject);
    });
  }
  ACENegotiate(codecName, resolve, reject) {
    this.callback({
      type: "create-offer-and-setLocalDescription-start",
      message: "createOffer&setLocalDescription",
    });
    this.pcclient_
      .createOffer()
      .then((sdp) => {
        // Delete vp8/vp9, just leave h264
        var codecs = ["H264/90000"];
        if (codecName) {
          let codecJson = {
            H264: ["H264/90000"],
            VP8: ["VP8/90000"],
            VP9: ["VP9/90000"],
            H265: ["H265/90000"],
          };
          codecs = codecJson[codecName];
        }
        this.callback({
          type: "create-offer-end",
          message: "createOffer创建成功",
        });
        sdp.sdp = reorderCodecs(sdp.sdp, "video", codecs);
        return this.pcclient_.setLocalDescription(sdp);
      })
      .then((sdp) => {
        return new Promise((zstdResolve) => {
          ZstdBrowser(sdp.sdp, this.cstreamingBuildVersion).then((res) => {
            zstdResolve({
              sdp: res,
              type: sdp.type,
            });
          });
        });
      })
      .then((sdp) => {
        this.callback({
          type: "create-offer-and-setLocalDescription-success",
          message: "createOffer&setLocalDescription",
        });
        let offer_req = this.msg_.getSdpOfferNotify();
        offer_req.req_msg.sdp = sdp.sdp;
        offer_req.req_msg.timestamp = this._getTimestamp();
        offer_req.req_msg.from = this.myself_.id;
        offer_req.req_msg.roomID = this.roomID_;
        offer_req.req_msg.to =
          this.another_ === undefined ? 0 : this.another_.id;

        if (resolve) {
          this.another_.setResolv(resolve);
        }
        this.callback({
          type: "send-offer-sdp-start",
          message: "将本地sdp发送给对方",
        });
        this.channel_.send(offer_req, (response) => {
          this.hb_timstamp = this._getNowMS();
          this.callback({
            type: "answer-success",
            message: "对方回应完成，媒体协商完成",
          });
          ZstdDecompress(response.sdp, this.cstreamingBuildVersion).then(
            (res) => {
              this.pcclient_
                .setRemoteDescription({
                  type: "answer",
                  sdp: res,
                })
                .catch((reason) => {
                  if (reject) {
                    reject(
                      "PeerConnection setRemoteDescription error===" + reason
                    );
                  }
                });
            }
          );
        });
      });
  }

  sendHeartBeat() {
    // check hb.
    if (
      this.hb_timstamp +
        this.HEARTBEAT_INTERVAL_MS * this.HEARTBEAT_TIMEOUT_TIMES <
      this._getNowMS()
    ) {
      logger.warn("HB timeout.");
      clearInterval(this.heartbeatTimer);
      this.channel_ && this.channel_.close();
      this._rejoin();
      return;
    }
    if (!this.channel_) return;
    var hb_req = this.msg_.getHeartBeatRequest();
    hb_req.req_msg.roomID = this.roomID_;
    hb_req.req_msg.timestamp = this._getTimestamp();
    hb_req.req_msg.peerID = this.myself_.id;

    this.channel_.send(
      hb_req,
      (response) => {
        if (response.result !== "success") {
          logger.error("Heartbeat request failed. reason:" + response.result);
          return;
        }
        this.hb_timstamp = this._getNowMS();
        if (response.networkInfo !== undefined) {
          this.networkInfo = response.networkInfo;
          // todo: notify ui
          logger.debug("Emit networkinfo.");
          this.safeEmit("on-network-info", this.networkInfo);
        }
      },
      false
    );
  }
  getRoomLists() {
    return new Promise((resolve, reject) => {
      logger.debug("Get room lists from /cs/getrooms");
      sendAsyncUrlRequest("GET", "/cs/getrooms")
        .then((result) => {
          var rooms = parseJSON(result);
          if (!rooms) {
            resolve();
            return;
          }
          resolve(rooms);
        })
        .catch((error) => {
          logger.error(
            "Initializing; error getting params from server: " + error.message
          );
          reject(error);
        });
    });
  }
  /********************** private functions ************************/
  _openPeerConnectionClient() {
    if (this.addBase64ImageCss) {
      this.addBase64ImageCss();
      this.addBase64ImageCss = null;
    }
    this._closePeerConnectionClient();
    if (this.pcclient_ === undefined) {
      this.callback({
        type: "create-webRTC-start",
        message: "开始创建webrtc",
      });
      this.pcclient_ = new PeerConnectionClient(this.params_);
      this.pcclient_.onicedisconnect = this._onicedisconnect.bind(this);
      this.pcclient_.onsignalingmessage = this._onsignalingmessage.bind(this);
      this.pcclient_.onremotestreamadded = this._onRemoteStreamAdded.bind(this);
      this.pcclient_.on("on-ice-success", () => {
        this.callback({
          type: "ice-success",
          message: "ice协商成功!",
        });
      });
      this.pcclient_.on("on-peer-error-status", (message) => {
        this.safeEmit("on-room-error-status", message);
      });
      this.PeerConnectionClientTimer = setInterval(() => {
        this.pcclient_ && this.pcclient_._getPeerConnectionStats();
      }, 1000);
      if (this.leaveNotifyStstus) {
        clearInterval(this.PeerConnectionClientTimer);
        this.PeerConnectionClientTimer = null;
      }
    }
  }
  _closePeerConnectionClient(status = true) {
    logger.debug(status, "_closePeerConnectionClient status");
    if (this.PeerConnectionClientTimer) {
      clearInterval(this.PeerConnectionClientTimer);
      this.PeerConnectionClientTimer = null;
    }
    // if (this.old_pcclient !== undefined) {
    //   this.old_pcclient.close();
    // }
    // if (this.pcclient_ !== undefined) {
    //   if (status) {
    //     this.old_pcclient = this.pcclient_;
    //   } else {
    //     this.old_pcclient = undefined;
    //     this.pcclient_.close();
    //   }
    //   this.pcclient_ = undefined;
    // }
    if (this.pcclient_ !== undefined) {
      this.pcclient_.close();
      this.pcclient_ = undefined;
    }
  }
  _getToken(serverParams) {
    return new Promise((resolve, reject) => {
      logger.debug("Initializing; retrieving params from /cs/token");
      if (!serverParams) {
        reject();
        return;
      }
      // Convert from server format to expected format.
      this.params_.roomID = serverParams.roomID;
      this.params_.iceServers = serverParams.iceServers;
      this.params_.wssUrl = serverParams.wssUrl;
      this.params_.peerID = serverParams.peerID;
      this.params_.wssUrlList = serverParams.wssUrlList;
      logger.debug(
        "Initializing; parameters from server======= " +
          JSON.stringify(this.params_)
      );
      resolve();
    });
  }

  /******************** Peer Connection callback begin *******************/
  _onsignalingmessage(message, type) {
    if (type === "candidate") {
      let cand_req = this.msg_.getCandidateNotify();
      cand_req.req_msg.timestamp = this._getTimestamp();
      cand_req.req_msg.from = this.myself_.id;
      cand_req.req_msg.roomID = this.roomID_;
      cand_req.req_msg.to = this.another_.id;
      console.log("message-candidate", message);
      cand_req.req_msg.candidate.sdp = "a=" + message.candidate;
      cand_req.req_msg.candidate.sdpMid = message.sdpMid;
      cand_req.req_msg.candidate.sdpMLineIndex = message.sdpMLineIndex;
      this.callback({
        type: "send-candidate",
        message: "将本地ice发送给对端",
      });
      this.channel_.send(cand_req, (response) => {
        //do nothing
      });
    }
  }
  _onicedisconnect() {
    /*
    if (this.heartbeatTimer !== undefined){
      clearInterval(this.heartbeatTimer);
    }
*/
    // this._rejoin();
    logger.debug(
      "_onicedisconnect: onLine = " +
        (navigator.onLine ? "网络连接正常 " : "网络连接已断开")
    );
    logger.debug(
      "_onicedisconnect: anotherLeaveNotify = " + this.anotherLeaveNotify
    );
    if (this.anotherLeaveNotify) {
      return;
    }
    if (this.resetTimer) {
      logger.debug("_onicedisconnect : messageID 1013 ,无需重连，等待1007过来");
      return;
    }
    if (
      this.channel_ !== undefined &&
      // this.pcclient_ === undefined &&
      this.channel_.getWebSocketState() === 1
    ) {
      // Notify ccs to reconcile
      this._iceReconcileNotify();
      //this._closePeerConnectionClient();
      // Notify the app pull
      this.safeEmit("on-ice-reconcile");
    }
  }
  _onRemoteStreamAdded(stream, transceiver) {
    this.another_.setMediaStream(stream, transceiver);
  }
  /******************** Signal Channel callback begin *******************/
  _onSignalChannelClosed(event, message) {
    /*
    if (this.heartbeatTimer !== undefined){
      clearInterval(this.heartbeatTimer);
    }
    */
    //this._rejoin();
  }
  _onMessageNotify(event, message) {
    this.hb_timstamp = this._getNowMS();
    if (event.messageID === 1005) {
      this.pcclient_.setCandidate(event.candidate);
    } else if (event.messageID === 1007) {
      const data = this.pcclient_.getPeerConnectionStates();
      if (
        data &&
        (data.signalingState !== "stable" ||
          data.iceGatheringState !== "complete" ||
          (data.iceConnectionState !== "connected" &&
            data.iceConnectionState !== "completed"))
      ) {
        logger.debug(
          "messageID 1007 ,signalingState:" + data.signalingState,
          " iceGatheringState:" + data.iceGatheringState,
          " iceConnectionState:" + data.iceConnectionState
        );
        this.safeEmit("on-user-join-notify");
      } else {
        logger.debug("messageID 1007 ,connect states success");
      }
      // if (
      //   data &&
      //   (data.signalingState === "closed" ||
      //     data.iceConnectionState === "failed" ||
      //     data.iceConnectionState === "closed")
      // ) {
      //   this.safeEmit("on-user-join-notify");
      // }
      if (this.resetTimer) {
        clearTimeout(this.resetTimer);
        this.resetTimer = null;
      }
    } else if (event.messageID === 1013) {
      // Peer leave
      if (this.resetTimer) {
        clearTimeout(this.resetTimer);
        this.resetTimer = null;
      }
      this.resetTimer = setTimeout(() => {
        if (this.another_ !== undefined && this.another_.id === event.peerID) {
          this.another_.leaveNotify();
          this.anotherLeaveNotify = true;
        }
      }, this.timeoutSeconds);
    } else if (event.messageID === 1021) {
      // console.log(this.another_, this.another_.id, event.from, "event.from");
      if (this.another_ !== undefined && this.another_.id === event.from) {
        this.another_.rotationNotify({
          width: event.width,
          height: event.height,
          rotation: event.rotation,
        });
      }
    } else if (event.messageID === 1023) {
      this.safeEmit("on-network-info", {
        rtt: event.rtt,
        lost: event.lost,
        jitter: event.jitter,
      });
    } else if (event.messageID === 1027) {
      //this._closePeerConnectionClient();
      // Notify the app pull
      this.safeEmit("on-ice-reconcile");
    } else if (event.messageID === 1029) {
      //this._closePeerConnectionClient();
      // Notify the app pull
      //console.warn(event, 1029, '你已经' + event.interval + '秒没有操作了');
      this.safeEmit("on-user-no-operation", {
        interval: event.interval,
      });
    } else if (event.messageID === 1029) {
      //this._closePeerConnectionClient();
      // Notify the app pull
      //console.warn(event, 1029, '你已经' + event.interval + '秒没有操作了');
      this.safeEmit("on-user-no-operation", {
        interval: event.interval,
      });
    } else if (event.messageID === 1033) {
      this.safeEmit("on-room-error-status", {
        type: "signal-connect",
        status: "error",
        code: event.code,
        message: event.message,
      });
    } else if (event.messageID === 1014) {
      // Peer leave
      this.safeEmit("on-room-error-status", {
        type: "passive-leave",
        status: "error",
        code: event.code,
        message: event.message,
      });
    } else if (event.messageID === 1512) {
      // Peer leave
      console.log("1512", event);
    } else if (event.messageID === 1035) {
      if (this.userMedia.videoStatus) {
        const { cameraId } = event; // 0 前置，1 后置
        this.getStream({
          codecName: event.codecName,
          enableVideo: true,
          cameraId,
        });
      } else {
        logger.debug("locationMediaConfig.video is false ");
      }
    } else if (event.messageID === 1037) {
      this.removeTracks("video");
    } else if (event.messageID === 1039) {
      if (this.userMedia.audioStatus) {
        this.getStream({ codecName: event.codecName, enableAudio: true });
      } else {
        logger.debug("locationMediaConfig.audio is false ");
      }
    } else if (event.messageID === 1041) {
      this.removeTracks("audio");
    } else if (event.messageID === 1527) {
      this.safeEmit("on-msg-notify", event);
    } else if (event.messageID === 1533) {
      this.safeEmit("on-msg-cime-input-view", event);
    } else if (event.messageID === 1539) {
      // 收到代理切换的通知，需要向服务的发送1540的请求，并将1539里获得的数据创建一个新的信令。
      this._resetChannel_(event);
    } else if (event.messageID === 9992) {
      this.safeEmit("on-timeout", event);
    }
  }
  // 代理切换，需要重新代理
  _resetChannel_(event) {
    this.sendProxyTraffic();
    if (event && !event.proxyUrl) {
      logger.debug("new SignalChannelNative proxyUrl is not");
      this.safeEmit("on-room-error-status", {
        type: "proxyUrl-not",
        status: "error",
        code: 1539,
        message: "new SignalChannelNative proxyUrl is not",
      });
      return;
    }
    this.params_.roomID = event.roomID;
    this.params_.wssUrl = event.proxyUrl;
    this.params_.peerID = event.peerID;
    // 创建新信令，并重新绑定监听事件
    logger.debug("create new SignalChannelNative");
    const newChannel_ = new SignalChannelNative(
      this.params_.wssUrl,
      this.params_.wssUrlList,
      this.callback
    );
    newChannel_.on("connection_closed", (event, message) => {
      this._onSignalChannelClosed(event, message);
    });
    // Listen notify
    newChannel_.on("message-notify", (event, message) => {
      this._onMessageNotify(event, message);
    });
    newChannel_.on("fast-reconnect-success", (event, message) => {
      this._onSignalChannelFastReconnectSuccess(event, message);
    });
    newChannel_.on("on-signal-error-status", (message) => {
      // 如果websocket失败，那么room将不会被渲染，则使用监听函数
      this.errCb(message);
    });
    // 监听链接
    newChannel_.open().then(() => {
      // 关闭旧信令
      logger.debug("close old SignalChannelNative ");
      this.channel_ && this.channel_.close();
      this.channel_ = undefined;
      this.channel_ = newChannel_;
    });
  }
  _onSignalChannelFastReconnectSuccess(event, message) {
    logger.debug(
      "Fast reconnect success.icestate:" + this.pcclient_ !== undefined
        ? this.pcclient_.getIceConnectionState()
        : "disconnected"
    );

    let roominfo_req = this.msg_.getRoomInfoRequest();
    roominfo_req.req_msg.timestamp = this._getTimestamp();
    roominfo_req.req_msg.peerID = this.myself_.id;
    roominfo_req.req_msg.roomID = this.roomID_;

    this.channel_.send(roominfo_req, (response) => {
      // Set peerid
      if (response.peers !== undefined && response.peers.length > 0) {
        this._createAnotherPeer(response.peers[0].peerID);
      }

      if (
        this.pcclient_ !== undefined &&
        this.pcclient_.getIceConnectionState() === "disconnected"
      ) {
        // Notify the ccs reconcile
        this._iceReconcileNotify();
        //this._closePeerConnectionClient();
        // Notify the app pull
        logger.debug("_onSignalChannelFastReconnectSuccess");
        this.safeEmit("on-ice-reconcile");
      } else {
        // rejoin or pclient is ok.
        //do nothing.
      }
    });
  }
  _onError(message) {
    console.log(message);
  }

  /******************** Signal Channel callback end *******************/
  _PeerLeave(id) {
    logger.debug("Delete Peer id:" + id);
    // Assign this Peer object to undefined.
    if (this.leaveNotifyStstus) {
      this.pcclient_.close();
      if (this.PeerConnectionClientTimer) {
        clearInterval(this.PeerConnectionClientTimer);
        this.PeerConnectionClientTimer = null;
      }
    }
    this.pcclient_ = undefined;
    this.another_ = undefined;
  }

  _getNowMS() {
    // var ts = new Date().getTime() & 0xffffffff;
    // ts = ts >>> 0;
    // return ts;
    return new Date().getTime();
  }

  _getTimestamp() {
    // var ts = new Date().getTime() & 0xffffffff;
    // ts = ts >>> 0;
    //
    // if (ts <= this.lastTimestamp_) {
    //   ts = this.lastTimestamp_ + 1;
    // }
    //
    // this.lastTimestamp_ = ts;
    //
    // return ts;

    let ts = new Date().getTime();
    if (ts <= this.lastTimestamp_) {
      ts = this.lastTimestamp_ + 1;
    }
    this.lastTimestamp_ = ts;
    return ts;
  }

  _getBitrateByResolution(width, height, fps) {
    var factor = 0.07;
    var resolution_product = width * height;
    if (resolution_product >= 1920 * 1080) {
      factor = 0.05;
    }

    let bitrate = resolution_product * fps * factor;

    bitrate = Math.floor(bitrate);

    if (bitrate > 6000000) bitrate = 6000000;
    else if (bitrate < 300000) bitrate = 300000;

    return bitrate;
  }
  _rejoin() {
    this.safeEmit("on-rejoin");
  }
  _createAnotherPeer(peerID) {
    if (this.another_ === undefined) {
      // Peer join
      this.another_ = new Peer(peerID, this.callback);
      this.anotherLeaveNotify = false;
      this.another_.onleave = this._PeerLeave.bind(this);
      this.another_.ontrack = (event) => {
        // 确保接收到的是音频流
        console.log(event, "确保接收到的是音频流");
      };
    } else {
      // Need to update peer id.
      this.another_.setId(peerID);
      logger.debug("The another peer " + peerID + " has been joined.");
    }
  }
  _iceReconcileNotify() {
    if (this.another_) {
      let ice_req = this.msg_.getIceReconcileNotify();
      ice_req.req_msg.timestamp = this._getTimestamp();
      ice_req.req_msg.from = this.myself_.id;
      ice_req.req_msg.roomID = this.roomID_;
      ice_req.req_msg.to = this.another_.id;
      this.channel_.send(ice_req, (response) => {
        //do nothing
      });
    }
  }

  // 设置分辨率
  setMediaConfig(data = { height: 1280, width: 1920 }) {
    return new Promise((resolve, reject) => {
      let media_req = this.msg_.updateMediaConfig();
      media_req.req_msg.timestamp = this._getTimestamp();
      media_req.req_msg.from = this.myself_.id;
      media_req.req_msg.roomID = this.roomID_;
      media_req.req_msg.to = this.another_.id;
      media_req.req_msg.peerID = this.myself_.id;
      // height: 1920,
      //     width: 1080,
      //     codecName: "H264",
      //     frameRate: 60,
      //     startBitrate: 10000, //10kbps
      //     minBitrate: 8000, //8kbps
      //     maxBitrate: 12000, //12kbps
      //     imageQuality: 1, // 画质
      //     mode: 1, // 模式
      if (!data) {
        reject("参数必须为json");
        return;
      }
      this._setMediaConfig(data || {});
      media_req.req_msg.mediaConfig.screen = this._mediaConfig;
      this.channel_.send(media_req, (response) => {
        //do nothing
        if (response.result === "success") {
          resolve(response);
        } else {
          reject(response);
        }
      });
    });
  }
  // 获取截图
  getScreenShotRequest(newType = 1, newInstanceId = "") {
    let type = Number(newType);
    return new Promise((resolve, reject) => {
      let instanceId =
        newInstanceId || this.option.sn || this.option.instanceId;
      if (![1, 2].includes(type)) {
        type = 1;
      }
      if (!instanceId) {
        reject({
          code: 10001,
          message: "请手动传入instanceId",
        });
        return;
      }
      let media_req = this.msg_.getScreenShotRequest();
      media_req.req_msg.timestamp = this._getTimestamp();
      media_req.req_msg.roomID = this.roomID_;
      media_req.req_msg.peerID = this.myself_.id;
      media_req.req_msg.instanceId = instanceId;
      media_req.req_msg.storageType = type;
      this.channel_.send(media_req, (response) => {
        //do nothing
        if (response.result === "success") {
          resolve(response);
        } else {
          reject(response);
        }
      });
    });
  }
  // 摇一摇
  sendShakeRequest(shakeDuration = 2000) {
    return new Promise((resolve, reject) => {
      let instanceId = this.option.sn || this.option.instanceId;
      let shake = this.msg_.sendShakeRequest();
      shake.req_msg.timestamp = this._getTimestamp();
      shake.req_msg.roomID = this.roomID_;
      shake.req_msg.peerID = this.myself_.id;
      shake.req_msg.instanceId = instanceId;
      shake.req_msg.shakeDuration = shakeDuration;
      this.channel_.send(shake, (response) => {
        //do nothing
        if (response.result === "success") {
          resolve(response);
        } else {
          reject(response);
        }
      });
    });
  }
  // 发送切换画质请求
  setSwitchImageQualityRequest(imageQuality, instanceId = "") {
    return new Promise((resolve, reject) => {
      if (!instanceId) {
        instanceId = this.option.sn || this.option.instanceId;
      }
      let quality = this.msg_.sendSwitchImageQualityRequest();
      quality.req_msg.timestamp = this._getTimestamp();
      quality.req_msg.roomID = this.roomID_;
      quality.req_msg.peerID = this.myself_.id;
      quality.req_msg.instanceId = instanceId;
      if (typeof imageQuality !== "number") {
        reject("画质必须为数字!");
      } else {
        quality.req_msg.imageQuality = imageQuality;
        this.channel_.send(quality, (response) => {
          //do nothing
          if (response.result === "success") {
            resolve(response);
          } else {
            reject(response);
          }
        });
      }
    });
  }
  // 发送旋转屏幕请求
  setRotateDeviceRequest(instanceId = "") {
    return new Promise((resolve, reject) => {
      if (!instanceId) {
        instanceId = this.option.sn || this.option.instanceId;
      }
      let device = this.msg_.setRotateDeviceRequest();
      device.req_msg.timestamp = this._getTimestamp();
      device.req_msg.roomID = this.roomID_;
      device.req_msg.peerID = this.myself_.id;
      device.req_msg.instanceId = instanceId;
      this.channel_.send(device, (response) => {
        //do nothing
        if (response.result === "success") {
          resolve(response);
        } else {
          reject(response);
        }
      });
    });
  }
  // 切换网络
  sendNetWorkChangeRequest(lineId) {
    return new Promise((resolve, reject) => {
      let shake = this.msg_.sendSwitchLineRequest();
      shake.req_msg.timestamp = this._getTimestamp();
      shake.req_msg.roomID = this.roomID_;
      shake.req_msg.peerID = this.myself_.id;
      shake.req_msg.instanceId = this.option.sn;
      shake.req_msg.lineId = lineId;
      this.channel_.send(shake, (response) => {
        //do nothing
        if (response.result === "success") {
          this._iceReconcileNotify();
          // this._closePeerConnectionClient()
          // // this.safeEmit("on-ice-network-reconcile");
          setTimeout(() => {
            this.safeEmit("on-ice-network-reconcile");
          }, 500);
          resolve(response);
        } else {
          reject(response);
        }
      });
    });
  }

  // 群控开始云机上传;
  startControlCloudPhoneRequestOld() {
    this.controlCloudUpStatus = true;
  }
  // 旧有的 发送群控信息
  sendCloudPhoneControlOld(event) {
    if (
      this.option.controlSnInfo &&
      this.option.controlSnInfo.instanceIds &&
      this.option.controlSnInfo.instanceIds.length &&
      this.controlCloudUpStatus
    ) {
      let controlSnInfo = this.option.controlSnInfo;
      let cloudPhoneControl = this.msg_.sendCloudPhoneControl();
      cloudPhoneControl.req_msg.timestamp = this._getTimestamp();
      cloudPhoneControl.req_msg.roomID = this.roomID_;
      cloudPhoneControl.req_msg.from = this.myself_.id;
      cloudPhoneControl.req_msg.event = event;
      const { instanceIds, width, height, format, quality, duration } =
        controlSnInfo;
      cloudPhoneControl.req_msg.to.instanceIds = instanceIds;
      if (width) {
        cloudPhoneControl.req_msg.to.width = Number(width);
      }
      if (height) {
        cloudPhoneControl.req_msg.to.height = Number(height);
      }
      if (format) {
        cloudPhoneControl.req_msg.to.format = format;
      }
      if (quality) {
        cloudPhoneControl.req_msg.to.quality = Number(quality);
      }
      if (duration) {
        cloudPhoneControl.req_msg.to.duration = this.controlCloudUpStatus
          ? Number(duration)
          : 0;
      }
      this.channel_.send(cloudPhoneControl, (response) => {
        //do nothing
      });
    }
  }
  // 旧有的停止云机上传
  stopControlCloudPhoneRequestOld() {
    if (
      this.option.controlSnInfo &&
      this.option.controlSnInfo.instanceIds &&
      this.option.controlSnInfo.instanceIds.length
    ) {
      this.controlCloudUpStatus = false;
      let controlSnInfo = this.option.controlSnInfo;
      let stopCloudPhoneControl = this.msg_.stopControlCloudPhone();
      stopCloudPhoneControl.req_msg.timestamp = this._getTimestamp();
      stopCloudPhoneControl.req_msg.roomID = this.roomID_;
      stopCloudPhoneControl.req_msg.from = this.myself_.id;
      stopCloudPhoneControl.req_msg.instanceIds = controlSnInfo.instanceIds;
      this.channel_.send(stopCloudPhoneControl, (response) => {
        //do nothing
      });
    }
  }
  //开启群控云机
  startControlCloudPhoneRequest() {
    return new Promise((resolve, reject) => {
      if (
        this.option.controlSnInfo &&
        this.option.controlSnInfo.instanceIds &&
        this.option.controlSnInfo.instanceIds.length
      ) {
        let controlSnInfo = this.option.controlSnInfo;
        let cloudPhoneControl = this.msg_.StartControlCloudPhoneRequestNew();
        cloudPhoneControl.req_msg.timestamp = this._getTimestamp();
        cloudPhoneControl.req_msg.roomID = this.roomID_;
        cloudPhoneControl.req_msg.from = this.myself_.id;
        const { instanceIds, width, height, format, quality, duration } =
          controlSnInfo;
        cloudPhoneControl.req_msg.to.instanceIds = instanceIds;
        if (width) {
          cloudPhoneControl.req_msg.to.width = Number(width);
        }
        if (height) {
          cloudPhoneControl.req_msg.to.height = Number(height);
        }
        if (format) {
          cloudPhoneControl.req_msg.to.format = format;
        }
        if (quality) {
          cloudPhoneControl.req_msg.to.quality = Number(quality);
        }
        if (duration) {
          cloudPhoneControl.req_msg.to.duration = Number(duration);
        }
        this.channel_.send(cloudPhoneControl, (response) => {
          //do nothing
          if (response.result === "success" && response.transactionId) {
            this.transactionId = response.transactionId;
            this.isOldMessage = false;
            resolve(response);
          } else {
            reject(response);
            this.isOldMessage = true;
            this.startControlCloudPhoneRequestOld();
          }
        });
      } else {
        reject("controlSnInfo.instanceIds 不能为空");
      }
    });
  }
  // 群控云机信息发送
  sendCloudPhoneControl(event) {
    if (this.isOldMessage) {
      this.sendCloudPhoneControlOld(event);
      return;
    }
    if (this.transactionId) {
      let cloudPhoneControl = this.msg_.CloudPhoneControlRequestNew();
      cloudPhoneControl.req_msg.timestamp = this._getTimestamp();
      cloudPhoneControl.req_msg.roomID = this.roomID_;
      cloudPhoneControl.req_msg.from = this.myself_.id;
      cloudPhoneControl.req_msg.event = event;
      cloudPhoneControl.req_msg.transactionId = this.transactionId;
      this.channel_.send(cloudPhoneControl, () => {});
    }
  }
  // 群控停止云机上传
  stopControlCloudPhoneRequest() {
    return new Promise((resolve, reject) => {
      if (this.isOldMessage) {
        this.stopControlCloudPhoneRequestOld();
        resolve("old stopControlCloudPhoneRequest");
        return;
      }
      if (this.transactionId) {
        let stopCloudPhoneControl = this.msg_.StopControlCloudPhoneRequestNew();
        stopCloudPhoneControl.req_msg.timestamp = this._getTimestamp();
        stopCloudPhoneControl.req_msg.roomID = this.roomID_;
        stopCloudPhoneControl.req_msg.from = this.myself_.id;
        stopCloudPhoneControl.req_msg.transactionId = this.transactionId;
        this.channel_.send(stopCloudPhoneControl, (response) => {
          //do nothing
          if (response.result === "success") {
            this.transactionId = "";
            resolve(response);
          } else {
            reject(response);
          }
        });
      } else {
        reject("请点击开始群控获取群控ID");
      }
    });
  }
  // 设置是否监听剪切板变化
  setListenClipboard(listenType = 0) {
    return new Promise((resolve, reject) => {
      const list = [0, 1];
      if (list.includes(Number(listenType))) {
        let ListenClipboard = this.msg_.SetListenClipboard();
        ListenClipboard.req_msg.timestamp = this._getTimestamp();
        ListenClipboard.req_msg.roomID = this.roomID_;
        ListenClipboard.req_msg.peerID = this.myself_.id;
        ListenClipboard.req_msg.listen = listenType;
        this.channel_.send(ListenClipboard, (response) => {
          //do nothing
          if (response.result === "success") {
            resolve(response);
          } else {
            reject(response);
          }
        });
      } else {
        reject({
          code: 10002,
          message: "是否监听剪切板参数只能为0和1， 0代表不监听，2代表监听。",
        });
      }
    });
  }

  /**
   * 设置自动断流时长
   * @param listenType
   * @returns {Promise<unknown>}
   * @constructor
   */
  SetNoOperationTime(noOperationTime = 5 * 60) {
    return new Promise((resolve, reject) => {
      let NoOperationTime = this.msg_.SetNoOperationTimeRequest();
      NoOperationTime.req_msg.timestamp = this._getTimestamp();
      NoOperationTime.req_msg.roomID = this.roomID_;
      NoOperationTime.req_msg.peerID = this.myself_.id;
      NoOperationTime.req_msg.noOperationTime = noOperationTime;
      this.channel_.send(NoOperationTime, (response) => {
        //do nothing
        if (response.result === "success") {
          resolve(response);
        } else {
          reject(response);
        }
      });
    });
  }
  /**
   * 设置云机键盘
   * @param inputMethodType
   * @returns {Promise<unknown>}
   * @constructor
   */
  SetSwitchInputMethod(inputMethodType = 1) {
    return new Promise((resolve, reject) => {
      const list = [1, 2];
      if (list.includes(Number(inputMethodType))) {
        let SwitchInputMethod = this.msg_.SetSwitchInputMethodRequest();
        SwitchInputMethod.req_msg.timestamp = this._getTimestamp();
        SwitchInputMethod.req_msg.roomID = this.roomID_;
        SwitchInputMethod.req_msg.peerID = this.myself_.id;
        SwitchInputMethod.req_msg.inputMethodType = inputMethodType;
        this.channel_.send(SwitchInputMethod, (response) => {
          //do nothing
          if (response.result === "success") {
            resolve(response);
          } else {
            reject(response);
          }
        });
      } else {
        reject({
          code: 10001,
          message: "键盘参数只能为1和2， 1代表云机键盘，2代表外部键盘。",
        });
      }
    });
  }
  SendTransparentMsgRequest({ packageName, text, instanceIds }) {
    return new Promise((resolve, reject) => {
      let TransparentMsg = this.msg_.SendTransparentMsgRequest();
      TransparentMsg.req_msg.timestamp = this._getTimestamp();
      TransparentMsg.req_msg.roomID = this.roomID_;
      TransparentMsg.req_msg.from = this.myself_.id;
      if (!text) {
        reject({
          code: 30001,
          message: "注入文本不能为空!",
        });
        return;
      }
      if (!packageName) {
        reject({
          code: 30002,
          message: "app名称不能为空!",
        });
        return;
      }
      TransparentMsg.req_msg.text = text || "";
      TransparentMsg.req_msg.packageName = packageName || "";
      TransparentMsg.req_msg.instanceIds = instanceIds || [];
      this.channel_.send(TransparentMsg, (response) => {
        //do nothing
        if (response.result === "success") {
          resolve(response);
        } else {
          reject(response);
        }
      });
    });
  }

  //开启视频群控云机
  startVideoControlCloudPhoneRequest(instanceIds) {
    return new Promise((resolve, reject) => {
      if (instanceIds && instanceIds.length) {
        let cloudVideoCPhoneControl =
          this.msg_.startVideoControlCloudPhoneRequest();
        cloudVideoCPhoneControl.req_msg.timestamp = this._getTimestamp();
        cloudVideoCPhoneControl.req_msg.roomID = this.roomID_;
        cloudVideoCPhoneControl.req_msg.from = this.myself_.id;
        cloudVideoCPhoneControl.req_msg.to.instanceIds = instanceIds;
        this.channel_.send(cloudVideoCPhoneControl, (response) => {
          //do nothing
          if (response.result === "success" && response.transactionId) {
            this.transactionId = response.transactionId;
            this.isOldMessage = false;
            resolve(response);
          } else {
            reject({
              message: "开启群控云机失败",
              type: "open-group-control-error",
              data: response,
            });
          }
        });
      } else {
        reject("请传入sn数组");
      }
    });
  }

  /**
   * 设置屏幕分辨率
   * @param mediaQuality
   * @returns {Promise<unknown>}
   * @constructor
   */
  setSendMediaQuality(mediaQuality = "1920*1280") {
    return new Promise((resolve, reject) => {
      let MediaQuality = this.msg_.sendMediaQuality();
      MediaQuality.req_msg.timestamp = this._getTimestamp();
      MediaQuality.req_msg.roomID = this.roomID_;
      MediaQuality.req_msg.peerID = this.myself_.id;
      MediaQuality.req_msg.instanceId =
        this.option.sn || this.option.instanceId;
      MediaQuality.req_msg.mediaQuality = mediaQuality;
      this.channel_.send(MediaQuality, (response) => {
        //do nothing
        if (response.result === "success") {
          resolve(response);
        } else {
          reject(response);
        }
      });
    });
  }

  /**
   * 吹一吹
   * @returns {Promise<unknown>}
   */
  setSendBlow() {
    return new Promise((resolve, reject) => {
      let blow = this.msg_.sendBlow();
      blow.req_msg.timestamp = this._getTimestamp();
      blow.req_msg.roomID = this.roomID_;
      blow.req_msg.peerID = this.myself_.id;
      blow.req_msg.instanceId = this.option.sn || this.option.instanceId;
      this.channel_.send(blow, (response) => {
        //do nothing
        if (response.result === "success") {
          resolve(response);
        } else {
          reject(response);
        }
      });
    });
  }
  sendProxyTraffic() {
    let proxy = this.msg_.proxyTraffic();
    proxy.req_msg.timestamp = this._getTimestamp();
    proxy.req_msg.roomID = this.roomID_;
    proxy.req_msg.peerID = this.myself_.id;
    this.channel_.send(proxy, () => {});
  }
}
