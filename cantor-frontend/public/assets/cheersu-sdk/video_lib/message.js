import { browserDeviceType } from "../video_lib/utils";

export default class Message {
  constructor() {
    this.termTypeJson = {
      phone: 1,
      pc: 2,
    };
  }
  isPC() {
    return browserDeviceType();
  }
  // response
  getUserJoinRequest() {
    const versionInfo = SDK_INFO; // eslint-disable-line no-undef
    var UserJoinRequest = {
      version: 1, // 32 位无符号整数
      timestamp: 0, // 32 位无符号整数
      messageID: 1001, // 32 位无符号整数, Join Room MessageID
      roomID: 0,
      /*lastPeerID:0, optional*/
      peerID: 0, // The requestor's ID
      role: "ccsclient", // 'ccs' or 'ccsclient'
      mediaConfig: {
        screen: {
          codecName: "H264", // ex: 'H264', 'VP8', 'VP9'
          frameRate: 30,
          height: 1920,
          width: 1080,
          // targetBitrate: 3000,
          startBitrate: 8000,
          minBitrate: 6000,
          maxBitrate: 12000,
          adptTermResolutionFlag: 0,
          imageQuality: 1, // 1: 高清，2：普通，3：高速，4：急速
          mode: 1, // 1. keep framerate; 2. keep resolution; 3. balanced
          scale: 1.0,
        },
        audio: {
          codecName: "opus", // ex: 'aac', 'opus'
          channels: 2,
          sampleRate: 48000,
        },
      },
      userConfig: {
        noOperationTime: 60 * 5,
        userAgent: navigator.userAgent,
        termType: 1, // this.termTypeJson[this.isPC()],//
        useCimiFlag: 0,
        inputMethodType: 1, // 1、默认 2、文本注入
      },
      build: {
        version:
          versionInfo && versionInfo.version ? versionInfo.version : "1.0.3",
        buildTime:
          versionInfo && versionInfo.time ? versionInfo.time : 1697444897821,
      },
    };

    var join = {
      req_msg: UserJoinRequest,
      res_key: "1002",
    };
    return join;
  }

  getSdpOfferNotify() {
    let request = {
      version: 1, // 32 位无符号整数
      timestamp: 0, // 32 位无符号整数
      messageID: 1003, // 32 位无符号整数, Join Room MessageID
      roomID: 0,
      from: 0, // Sender's peerID
      to: 0, // Receiver's PeerID
      sdp: "",
    };

    let offer_req = {
      req_msg: request,
      res_key: "1004",
    };

    return offer_req;
  }

  getCandidateNotify() {
    let request = {
      version: 1, // 32 位无符号整数
      timestamp: 0, // 32 位无符号整数
      messageID: 1005, // 32 位无符号整数, Join Room MessageID
      roomID: 0,
      from: 0, // Sender's peerID
      to: 0, // Receiver's PeerID
      candidate: {
        sdpMLineIndex: -1,
        sdpMid: "",
        sdp: "",
      },
    };

    let cand_req = {
      req_msg: request,
    };

    return cand_req;
  }

  getUserLeaveRequest() {
    let request = {
      version: 1, // 32 位无符号整数
      timestamp: 0, // 32 位无符号整数
      messageID: 1011, // 32 位无符号整数, Join Room MessageID
      roomID: 0,
      peerID: 0, // The requestor's ID
    };
    let leave_req = {
      req_msg: request,
      res_key: "1012",
    };

    return leave_req;
  }

  getHeartBeatRequest() {
    let request = {
      version: 1, // 32 位无符号整数
      timestamp: 0, // 32 位无符号整数
      messageID: 1019, // 32 位无符号整数
      roomID: 0,
      peerID: 0, // Client's PeerID
    };
    let hb_req = {
      req_msg: request,
      res_key: "1020",
    };

    return hb_req;
  }
  getRoomInfoRequest() {
    var getRoomInfoRequest = {
      version: 1, // 32 位无符号整数
      timestamp: 0, // 32 位无符号整数
      messageID: 1025, // 32 位无符号整数, Join Room MessageID
      roomID: 0,
      peerID: 0, // The requestor's ID
    };
    var roomInfo = {
      req_msg: getRoomInfoRequest,
      res_key: "1026",
    };
    return roomInfo;
  }

  getIceReconcileNotify() {
    let iceReconcileNotify = {
      version: 1, // 32 位无符号整数
      timestamp: 0, // 32 位无符号整数
      messageID: 1027, // 32 位无符号整数
      roomID: 0,
      from: 0, // Client's PeerID
      to: 0,
    };
    let ice_req = {
      req_msg: iceReconcileNotify,
    };

    return ice_req;
  }
  // 动态修改分辨率
  updateMediaConfig() {
    let mediaConfig = {
      version: 1, // 32 位无符号整数
      timestamp: 0, // 32 位无符号整数
      messageID: 1015, // 32 位无符号整数
      roomID: 0,
      from: 0,
      to: 0,
      peerID: 0,
      mediaConfig: {
        screen: {
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
        },
      },
    };
    let MediaConfig = {
      req_msg: mediaConfig,
      res_key: "1016",
    };
    return MediaConfig;
  }

  // 发送截图请求
  getScreenShotRequest() {
    let mediaConfig = {
      version: 1, // 32 位无符号整数
      timestamp: 0, // 32 位无符号整数
      messageID: 1503, // 32 位无符号整数
      roomID: 0,
      peerID: 0, // Client's PeerID
      instanceId: "",
      storageType: 1, // 1 local  2 s3
    };
    let ScreenShotRequest = {
      req_msg: mediaConfig,
      res_key: "1504",
    };
    return ScreenShotRequest;
  }
  // 发送摇一摇
  sendShakeRequest() {
    let shakeConfig = {
      version: 1, // 32 位无符号整数
      timestamp: 0, // 32 位无符号整数
      messageID: 1507, // 32 位无符号整数
      roomID: 0,
      peerID: 0, // Client's PeerID
      instanceId: 1, // the container sn
      shakeDuration: 2000, // the duration of the shake
    };
    let sendShakeRequest = {
      req_msg: shakeConfig,
      res_key: "1508",
    };
    return sendShakeRequest;
  }
  sendCloudPhoneControl() {
    let cloudPhoneConfig = {
      version: 1, // 32 位无符号整数
      timestamp: 0, // 32 位无符号整数
      messageID: 1521, // 32 位无符号整数
      roomID: 0,
      from: 0, // Client's PeerID
      event: "", // event 结构就是具体的操控事件结构，参考操控协议，前端以 String 的形式填充此子丢按的值
      to: {
        instanceIds: [],
        width: 640,
        height: 360,
        format: "jpeg",
        quality: 70,
        duration: 5000,
      },
    };
    let cloudPhoneControl = {
      req_msg: cloudPhoneConfig,
    };
    return cloudPhoneControl;
  }
  // 切换线路
  sendSwitchLineRequest() {
    let switchLineConfig = {
      version: 1, // 32 位无符号整数
      timestamp: 0, // 32 位无符号整数
      messageID: 1511, // 32 位无符号整数
      roomID: 0,
      peerID: 0, // Client's PeerID
      instanceId: 1, // the container sn
      lineId: 0,
    };
    let switchLineControl = {
      req_msg: switchLineConfig,
      res_key: "1512",
    };
    return switchLineControl;
  }

  // 切换画质
  sendSwitchImageQualityRequest() {
    let imageQualityConfig = {
      version: 1, // 32 位无符号整数
      timestamp: 0, // 32 位无符号整数
      messageID: 1513, // 32 位无符号整数
      roomID: 0,
      peerID: 0, // Client's PeerID
      instanceId: 1, // the container sn
      imageQuality: 1, // 1、2、3、4
    };
    return {
      req_msg: imageQualityConfig,
      res_key: "1514",
    };
  }

  // 发送旋转屏幕请求
  setRotateDeviceRequest() {
    let deviceConfig = {
      version: 1, // 32 位无符号整数
      timestamp: 0, // 32 位无符号整数
      messageID: 1517, // 32 位无符号整数
      roomID: 0,
      peerID: 0, // Client's PeerID
      instanceId: 1, // the container sn
    };
    let deviceConfigRequest = {
      req_msg: deviceConfig,
      res_key: "1518",
    };
    return deviceConfigRequest;
  }

  // 发送停止群控上传指令
  stopControlCloudPhone() {
    let stopControl = {
      version: 1, // 32 位无符号整数
      timestamp: 0, // 32 位无符号整数
      messageID: 1519, // 32 位无符号整数
      roomID: 0,
      from: 0, // The master control client's PeerID
      instanceIds: [], // the container sn
    };
    let stopControlRequest = {
      req_msg: stopControl,
      res_key: "1520",
    };
    return stopControlRequest;
  }

  // 开启云手机群控
  StartControlCloudPhoneRequestNew() {
    let cloudPhoneConfig = {
      version: 1, // 32 位无符号整数
      timestamp: 0, // 32 位无符号整数
      messageID: 1523, // 32 位无符号整数
      roomID: 0,
      from: 0, // Client's PeerID
      event: "", // event 结构就是具体的操控事件结构，参考操控协议，前端以 String 的形式填充此子丢按的值
      to: {
        instanceIds: [],
        width: 640,
        height: 360,
        format: "jpeg",
        quality: 70,
        duration: 5000,
      },
    };
    let cloudPhoneControl = {
      req_msg: cloudPhoneConfig,
      res_key: "1524",
    };
    return cloudPhoneControl;
  }

  //  发送云手机群控信息
  CloudPhoneControlRequestNew() {
    let sendPhone = {
      version: 1, // 32 位无符号整数
      timestamp: 0, // 32 位无符号整数
      messageID: 1521, // 32 位无符号整数
      roomID: 0,
      from: 0, // The master control client's PeerID
      event: "",
      transactionId: "",
    };
    let sendPhoneControl = {
      req_msg: sendPhone,
    };
    return sendPhoneControl;
  }

  // 停止云手机群控
  StopControlCloudPhoneRequestNew() {
    let StopControl = {
      version: 1, // 32 位无符号整数
      timestamp: 0, // 32 位无符号整数
      messageID: 1519, // 32 位无符号整数
      roomID: 0,
      from: 0, // The master control client's PeerID
      transactionId: "",
    };
    let stopPhoneControl = {
      req_msg: StopControl,
    };
    return stopPhoneControl;
  }

  /**
   * 设置是否监听剪切板变化
   */
  SetListenClipboard() {
    let ClipboardRequest = {
      version: 1, // 32 位无符号整数
      timestamp: 0, // 32 位无符号整数
      messageID: 1045, // 32 位无符号整数
      roomID: 0,
      peerID: 0, // Client's PeerID
      listen: 0, // 0: 不监听，1：监听
    };
    let clipboardControl = {
      req_msg: ClipboardRequest,
      res_key: "1046",
    };
    return clipboardControl;
  }

  /**
   * 设置自动断流时长
   * @returns {{peerID: number, messageID: number, version: number, roomID: number, timestamp: number, noOperationTime: number}}
   * @constructor
   */
  SetNoOperationTimeRequest() {
    let NoOperationTime = {
      version: 1, // 32 位无符号整数
      timestamp: 0, // 32 位无符号整数
      messageID: 1047, // 32 位无符号整数
      roomID: 0,
      peerID: 0, // Client's PeerID
      noOperationTime: 5 * 60,
    };
    let NoOperationTimeRequest = {
      req_msg: NoOperationTime,
      res_key: "1048",
    };
    return NoOperationTimeRequest;
  }

  /**
   * 设置键盘类型
   * @constructor
   */
  SetSwitchInputMethodRequest() {
    let SwitchInputMethod = {
      version: 1, // 32 位无符号整数
      timestamp: 0, // 32 位无符号整数
      messageID: 1509, // 32 位无符号整数
      roomID: 0,
      peerID: 0, // Client's PeerID
      inputMethodType: -1,
    };
    let SwitchInputMethodRequest = {
      req_msg: SwitchInputMethod,
      res_key: "1510",
    };
    return SwitchInputMethodRequest;
  }

  /**
   * 向指定的应用包发送信息
   * @constructor
   */
  SendTransparentMsgRequest() {
    let TransparentMsg = {
      version: 1, // 32 位无符号整数
      timestamp: 0, // 32 位无符号整数
      messageID: 1525, // 32 位无符号整数
      roomID: 0,
      from: 0, // The master control client's PeerID
      instanceIds: [], // the container sn
      text: "",
      packageName: "",
    };
    let TransparentMsgRequest = {
      req_msg: TransparentMsg,
      res_key: "1526",
    };
    return TransparentMsgRequest;
  }

  startVideoControlCloudPhoneRequest() {
    let videoControl = {
      version: 1,
      timestamp: 0,
      messageID: 1528,
      roomID: 0,
      from: 0,
      to: {
        instanceIds: [],
      },
    };
    let videoControlRequest = {
      req_msg: videoControl,
      res_key: "1529",
    };
    return videoControlRequest;
  }
  // 客户端发送切换分辨率消息
  sendMediaQuality() {
    const sendMediaQuality = {
      version: 1,
      timestamp: 0,
      messageID: 1537,
      roomID: "",
      peerID: "",
      instanceId: "",
      mediaQuality: "",
    };
    return {
      req_msg: sendMediaQuality,
      res_key: "1538",
    };
  }

  // 吹一吹
  sendBlow() {
    const blow = {
      version: 1,
      timestamp: 0,
      messageID: 1535,
      roomID: "",
      peerID: "",
      instanceId: "",
    };
    return {
      req_msg: blow,
      res_key: "1536",
    };
  }

  // 对1539代理切换后做出的反应
  proxyTraffic() {
    const proxy = {
      version: 1,
      timestamp: 0,
      messageID: 1540,
      roomID: "",
      peerID: "",
    };
    return {
      req_msg: proxy,
    };
  }
}
