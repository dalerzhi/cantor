import JMuxer from "./jmuxer";
import PacketBuffer from "./packetBuffer";
import { signature } from "../public/public";
import { ajaxCloud } from "../lib/ajax";
import ParserWorker from "./parserWorker";
import Event from "./util/event";
import JmuxerMessage from "./message";
const defaultData = {
  containerId: "container",
  prefixName: "videoPlayer",
  baseUrl: "https://192.168.50.30:8443",
  instanceContainer: [],
  videoConfig: {
    width: 360,
    height: 640,
  },
};

class JmuxerSDK extends Event {
  constructor(data = {}) {
    super("JmuxerSDK");
    this.maxReconnectNum = 10;
    this.clientInfo = {};
    // 调度链接
    this.curlWs = null;
    this.curlWsTimer = null;
    this.curlWsInterval = 20 * 1000;
    this.curlWsReconnectNum = 0;
    this.curlWsClientClose = false;
    this.curlLastTime = Date.now();
    this.curlProxyUrl = null;
    // 流链接
    this.murlWsJson = {};
    this.murlWsInterval = 10 * 1000;
    this.WebSocketOPEN = WebSocket.OPEN;
    // 解析器
    this.jmuxerJson = {};
    this.packetBufferJson = {};

    this.options = { ...defaultData, ...data };
    this.prefixName = this.options.prefixName;
    this.containerId = this.options.containerId;
    this.seq_no = 0;
    this.changeClientInfo = null;
    this.jmuxerMessage = new JmuxerMessage(2);
    this.isMySelf = false;
    this.onError = function () {};
    this.onLifeCycle = function () {};
    this.onDirection = function () {};
    if (data.callback && data.callback.onError) {
      this.onError = data.callback.onError;
    }
    if (data.callback && data.callback.onLifeCycle) {
      this.onLifeCycle = data.callback.onLifeCycle;
    }
    if (data.callback && data.callback.onDirection) {
      this.onDirection = data.callback.onDirection;
    }
    // 重连时间
    this.reconnectionTime = 1000 * 3;
    // 流id与instance对照表
    const list = this.options.instanceContainer;
    const instanceTostreamIdMap = {};
    for (let i = 0; i < list.length; i++) {
      instanceTostreamIdMap[list[i]] = "";
    }
    this.instanceTostreamIdMap = instanceTostreamIdMap;
    this.isCurlStatusFiest = true;
    if (
      this.options.videoConfig &&
      this.options.videoConfig.width &&
      this.options.videoConfig.height
    ) {
      this.videoConfig = this.options.videoConfig;
    } else {
      this.videoConfig = {
        width: 360,
        height: 640,
      };
    }
  }

  /**
   * 初始化信息
   */
  init() {
    signature(this.options.config, this.options.ak, this.options.sk).then(
      (data) => {
        ajaxCloud({
          url: this.options.baseUrl + `/coordinate/api/v1/getMts`,
          method: "POST",
          data,
        })
          .then((res) => {
            // console.log("mts info", res);
            this.join(res);
          })
          .catch((err) => {});
      }
    );
  }
  sendLifeCycle(data) {
    this.onLifeCycle(data);
  }
  /**
   * 初始化群控界面
   * @param data
   */
  join(data, status = true) {
    this.sendLifeCycle({
      type: "start-join",
      message: "初始化配置参数",
    });
    this.clientInfo = data;

    let { addConnectInfos, cUrl } = data;
    if (data.failInstanceStreams && data.failInstanceStreams.length) {
      this.onError({
        type: "create-instance-error",
        data: data.failInstanceStreams,
        message: "错误的实例对象",
      });
    }
    if (addConnectInfos && addConnectInfos.length === 0) {
      this.onError({
        type: "create-mUrls-error",
        data: data.addConnectInfos,
        message: "可创建的推流数据为空",
      });
      return;
    }
    if (!cUrl) {
      this.onError({
        type: "create-cUrl-error",
        data: data,
        message: "调度信令 cUrl 字段不存在。",
      });
      return;
    }
    let instanceStreams = [];
    let mUrls = [];
    // 获取所有的 murlWs
    for (let i = 0; i < addConnectInfos.length; i++) {
      const item = addConnectInfos[i];
      // 获取所有的 instanceStreams
      instanceStreams.push(...item.instanceStreams);
      mUrls.push(item);
    }
    // const { mUrls, cUrl, instanceStreams } = data;
    // 创建视频标签和解析器,先一部初始化
    for (let i = 0; i < instanceStreams.length; i++) {
      // 记录对照表
      this.instanceTostreamIdMap[instanceStreams[i].instanceId] =
        instanceStreams[i].streamId;
      this.createVideoAndMtspParser(
        this.prefixName + instanceStreams[i].streamId
      );
    }
    this.sendLifeCycle({
      type: "create-buffer-jmuxer",
      message: "创建解析器与构造器",
    });
    // 创建流通到链接
    for (let i = 0; i < mUrls.length; i++) {
      this.createMurlWs(mUrls[i].mtsUrl, mUrls[i].instanceStreams);
    }
    this.sendLifeCycle({
      type: "create-murl",
      message: "创建流通道信令",
    });
    // 创建调度链接
    if (status && cUrl) {
      this.createCurlWs(cUrl);
      this.sendLifeCycle({
        type: "create-curlWs",
        message: "创建调度信令",
      });
    }
  }

  /**
   * mts 断开后重新链接
   */
  resetMut(data) {
    let { addConnectInfos, removeConnectInfos } = data;
    let removeMUrls = [];
    let failInstances = [];
    let instanceStreams = [];
    let mUrls = [];
    // 删除需要移除的video和流通道
    for (let i = 0; i < removeConnectInfos.length; i++) {
      const item = removeConnectInfos[i];
      removeMUrls.push(item.mtsUrl);
      const instanceStreams = item.instanceStreams;
      failInstances.push(...instanceStreams);
    }
    // 删除销毁的mturl 和 实例
    this.remove(removeMUrls, failInstances, true);
    // 获取所有的 murlWs
    for (let i = 0; i < addConnectInfos.length; i++) {
      const item = addConnectInfos[i];
      // 获取所有的 instanceStreams
      instanceStreams.push(...item.instanceStreams);
      mUrls.push(item);
    }
    // 创建视频标签和解析器,先一部初始化
    for (let i = 0; i < instanceStreams.length; i++) {
      this.instanceTostreamIdMap[instanceStreams[i].instanceId] =
        instanceStreams[i].streamId;
      this.createVideoAndMtspParser(
        this.prefixName + instanceStreams[i].streamId
      );
    }
    // 创建流通到链接
    for (let i = 0; i < mUrls.length; i++) {
      this.createMurlWs(mUrls[i].mtsUrl, mUrls[i].instanceStreams, false, true);
    }
  }
  /**
   * 翻页后重新卸掉关系
   * @param data
   */
  resetJoin(data) {
    this.fristData = data;
    if (data.failInstanceStreams && data.failInstanceStreams.length) {
      this.onError({
        type: "page-turn-error",
        data: data.failInstanceStreams,
        message: "翻页失败的实例对象",
      });
    }
    // 如果是自己触发，则直接销毁创建
    if (this.isMySelf) {
      this.sendDeleteResources();
      this.sendAddResources();
      this.isMySelf = false;
    } else {
      // 否则暴露出去，由对方控制什么时候销毁创建
      this.sendDeleteResources();
      this.sendAddResources();
      this.dispatch("renderingCompleted");
    }
  }
  // 删除对应实例和资源
  sendDeleteResources() {
    let data = this.fristData;
    const clientWsList = [];
    const instanceIdToStreamids = {};
    for (let key in this.murlWsJson) {
      clientWsList.push(key);
      const list = this.murlWsJson[key].streamidList;
      for (let i = 0; i < list.length; i++) {
        instanceIdToStreamids[list[i].instanceId] = list[i].streamId;
      }
    }
    const { removeConnectInfos, repeatInfos, addConnectInfos } = data;
    // 之前遗留的链接
    const repeatInfoMtsUrlList = repeatInfos.map((x) => x.mtsUrl);
    const removeMUrls = [];
    const failInstances = [];

    const defaultRemoveWs = removeConnectInfos.map((x) => x.mtsUrl);
    const defaultAddWs = addConnectInfos.map((x) => x.mtsUrl);

    // 删除需要移除的video和流通道
    for (let i = 0; i < removeConnectInfos.length; i++) {
      const item = removeConnectInfos[i];
      const instanceStreams = item.instanceStreams;
      // 如果不存在遗留的mts，则断开mts推流，只对steams进行删除
      if (
        !(
          repeatInfoMtsUrlList.includes(item.mtsUrl) ||
          defaultAddWs.includes(item.mtsUrl)
        )
      ) {
        removeMUrls.push(item.mtsUrl);
      } else {
        // 拿到需要移除的实例ID
        const ids = instanceStreams.map((x) => x.streamId);
        // 拿到对应流链接上的实例对象
        if (this.murlWsJson[item.mtsUrl]) {
          let list = this.murlWsJson[item.mtsUrl].streamidList;
          // 拿到所有不需要移除的实例ID
          list = list.filter((x) => !ids.includes(x.streamId));
          this.murlWsJson[item.mtsUrl].streamidList = list;
        }
      }
      failInstances.push(...instanceStreams);
    }
    console.log(removeMUrls, failInstances, "removeMUrls new");
    // 删除销毁的mturl 和 实例
    this.remove(removeMUrls, failInstances, true);
    // this.fristData = null;
  }
  // 添加对应资源
  sendAddResources() {
    let data = this.fristData;
    const addMUrls = [];
    const addInstances = [];
    const sendKeyframeStreams = {};
    const clientWsList = [];
    const instanceIdToStreamids = {};
    for (let key in this.murlWsJson) {
      clientWsList.push(key);
      const list = this.murlWsJson[key].streamidList;
      for (let i = 0; i < list.length; i++) {
        instanceIdToStreamids[list[i].instanceId] = list[i].streamId;
      }
    }
    const { removeConnectInfos, repeatInfos, addConnectInfos } = data;
    // 之前遗留的链接
    const repeatInfoMtsUrlList = repeatInfos.map((x) => x.mtsUrl);
    const defaultRemoveWs = removeConnectInfos.map((x) => x.mtsUrl);
    for (let i = 0; i < addConnectInfos.length; i++) {
      const item = addConnectInfos[i];
      // 如果不存在，则进行连接。否则进行添加。
      const instanceStreams = item.instanceStreams;
      if (
        !(
          repeatInfoMtsUrlList.includes(item.mtsUrl) ||
          defaultRemoveWs.includes(item.mtsUrl) ||
          clientWsList.includes(item.mtsUrl)
        )
      ) {
        addMUrls.push(item);
      } else {
        if (!sendKeyframeStreams[item.mtsUrl]) {
          sendKeyframeStreams[item.mtsUrl] = [];
        }
        sendKeyframeStreams[item.mtsUrl].push(...instanceStreams);
      }
      addInstances.push(...instanceStreams);
    }
    // 创建新的解析器
    for (let i = 0; i < addInstances.length; i++) {
      // 判断如果当前页面存在相同的instanceId， 则删除旧有的streamId
      if (instanceIdToStreamids[addInstances[i].instanceId]) {
        this.remove(
          [],
          [
            {
              streamId: instanceIdToStreamids[addInstances[i].instanceId],
              instanceId: addInstances[i].instanceId,
            },
          ],
          true
        );
      }
      this.instanceTostreamIdMap[addInstances[i].instanceId] =
        addInstances[i].streamId;
      this.createVideoAndMtspParser(this.prefixName + addInstances[i].streamId);
    }

    // 创建流通到链接
    for (let i = 0; i < addMUrls.length; i++) {
      this.createMurlWs(
        addMUrls[i].mtsUrl,
        addMUrls[i].instanceStreams,
        false,
        true
      );
    }
    // 将新建的video发送关键帧请求
    for (let key in sendKeyframeStreams) {
      if (this.murlWsJson[key]) {
        // 将新建的实例ID关联到对应的流链接上，保持心跳。
        this.murlWsJson[key].streamidList.push(...sendKeyframeStreams[key]);
        const ws = this.murlWsJson[key].ws;
        const ids = sendKeyframeStreams[key].map((x) => Number(x.streamId));
        this.getRequestKeyframes(ws, ids);
      }
    }
    this.changeClientInfo = { ...data };
  }

  /**
   * 创建视频并将其加入到dom中
   * @param videoPlayerId  视频id
   */
  createVideo(videoPlayerId) {
    const playId = videoPlayerId.replace(/\D/g, "");
    let divId = "";
    for (let key in this.instanceTostreamIdMap) {
      if (this.instanceTostreamIdMap[key].toString() === playId.toString()) {
        divId = key;
        break;
      }
    }
    let video = document.getElementById(videoPlayerId);
    if (!video) {
      video = document.createElement("video");
      video.setAttribute("id", videoPlayerId);
      video.setAttribute("width", this.videoConfig.width);
      video.setAttribute("height", this.videoConfig.height);
      video.setAttribute("title", divId);
    }
    let div = document.getElementById(divId);
    if (!div) {
      document.getElementById(this.containerId).appendChild(video);
    } else {
      div.appendChild(video);
    }
  }
  // createVideo(videoPlayerId) {
  //   let video = document.getElementById(videoPlayerId);
  //     let divId = "";
  //     for (let key in this.instanceTostreamIdMap) {
  //       if (this.instanceTostreamIdMap[key].toString() === playId.toString()) {
  //         divId = key;
  //         break;
  //       }
  //     }
  //   if (!video) {
  //     video = document.createElement("video");
  //     video.setAttribute("id", videoPlayerId);
  //     video.setAttribute("width", this.videoConfig.width);
  //     video.setAttribute("height", this.videoConfig.height);
  //     video.setAttribute("title", divId);
  //   }
  //   let div = document.getElementById(this.containerId);
  //   div.appendChild(video);
  // }
  /**
   * 重新更新video样式
   * @param videoPlayerId
   * @param data
   */
  resetVideoStyle(videoPlayerId, data) {
    let video = document.getElementById(videoPlayerId);
    if (video) {
      let { width, height } = this.videoConfig;
      let newWidth = width;
      let newHeight = height;
      if (data.videoWidth > data.videoHeight) {
        newWidth = height;
        newHeight = width;
      }
      video.setAttribute("width", newWidth);
      video.setAttribute("height", newHeight);
    }
  }
  /**
   * 创建流通到, 一个流通道可能有多个视频流.
   * @param wsUrl
   *   * @param streamids
   *     * @param status
   *       * @param connectionKeyframe
   */
  createMurlWs(
    wsUrl,
    streamids = [],
    status = false,
    connectionKeyframe = false
  ) {
    if (!this.murlWsJson[wsUrl]) {
      this.murlWsJson[wsUrl] = {
        ws: null,
        connectStatus: 0, // 0未链接  1连接中 2主动断开 3切换页面断开 4异常断开
        murlWsReconnectNum: 0,
        murlWsClientClose: false,
        streamidList: streamids,
      };
    }
    // 初始化 mtsp解析
    let parserWorker = new ParserWorker();
    const ws = new WebSocket(wsUrl);
    const list = wsUrl.split("/");
    let seq_no = 0;
    let lastTime = Date.now();
    ws.binaryType = "arraybuffer";
    ws.onopen = () => {
      this.murlWsJson[wsUrl].murlWsReconnectNum = 0;
      this.murlWsJson[wsUrl].connectStatus = 1;

      // 如果是重连的,则发送请求关键帧,以及清空缓存.
      if (status) {
        let ids = streamids.map((x) => x.streamId);
        for (let i = 0; i < ids.length; i++) {
          const streamid = this.prefixName + ids[i];
          // 删除旧的解析器
          this.deleteVideoAndMtspParser(streamid);
          // 创建新的解析器
          this.createVideoAndMtspParser(streamid);
        }
        // 发送请求关键帧
        this.getRequestKeyframes(ws, ids);
      } else {
        this.sendLifeCycle({
          type: "create-murl-success",
          message: "创建流通道信令成功",
        });
      }
      if (connectionKeyframe) {
        let ids = streamids.map((x) => x.streamId);
        this.getRequestKeyframes(ws, ids);
      }
    };
    ws.onmessage = (event) => {
      this.sendCurlHeartbeatRequest();
      // 定时器，超过20S发送一次心跳
      if (Date.now() - lastTime > 1000 * 20) {
        seq_no += 1;
        lastTime = Date.now();
        let objectToBinary = this.jmuxerMessage.mUrlHeartbeatRequest(
          list[list.length - 2],
          list[list.length - 1],
          seq_no
        );
        ws.send(objectToBinary);
      }
      parserWorker.postMessage(event.data);
    };
    parserWorker.onmessageBack = (data) => {
      const { status, hdr, payload, err } = data;
      if (status) {
        const pt = hdr.pt;
        // pt= 0 为消息通知
        if (pt === 0) {
          // 1005 为屏幕发生旋转通知
          if (hdr.id.messageid === 1005) {
            try {
              const data = JSON.parse(this.Uint8ArrayToString(payload));
              // 确定选择流的ID
              const streamid = this.prefixName + data.streamid;
              // 创建新的解析器
              this.createVideoAndMtspParser(streamid);
              // 匹配对应的流的video标签
              // this.resetVideoStyle(streamid, data);
              this.getRequestKeyframes(ws, [data.streamid]);
              // let map = this.instanceTostreamIdMap;
              // for (let key in map) {
              //   if (Number(map[key]) === Number(data.streamid)) {
              //     this.onDirection({
              //       instanceId: key,
              //       width: data.videoWidth,
              //       height: data.videoHeight,
              //     });
              //   }
              // }
            } catch (e) {
              console.log("messageId:" + hdr.id.messageid, e);
            }
          } else if (hdr.id.messageid === 1020) {
            console.log(hdr.id.messageid, "1020");
          }
        } else {
          const streamid = this.prefixName + hdr.id.streamid;
          if (this.packetBufferJson && this.packetBufferJson[streamid]) {
            let data = {
              ...hdr,
              wsUrl,
            };
            this.packetBufferJson[streamid].addPacket(
              data,
              payload,
              (frame) => {
                this.jmuxerJson[streamid].feed({
                  video: frame, // 将 H.264 数据传递给 JMuxer
                });
              }
            );
          }
        }
      } else {
        console.log(err);
        ws.close();
      }
    };

    ws.onclose = () => {
      console.log(
        "MtspParser Disconnected from WebSocket server objectToBinary"
      );
      parserWorker && parserWorker.clear();
      parserWorker = null;
      const status = this.murlWsJson[wsUrl].murlWsClientClose;
      if (!status) {
        // 拿到重连次数
        let reconnectNum = (this.murlWsJson[wsUrl].murlWsReconnectNum += 1);
        // 重连次数小于10次
        if (reconnectNum < this.maxReconnectNum) {
          console.log("murlWs " + wsUrl + " reconnect num is " + reconnectNum);
          // 创建新的流通道
          const streamidList = this.murlWsJson[wsUrl].streamidList;
          setTimeout(() => {
            const statusNow = this.murlWsJson[wsUrl].murlWsClientClose;
            // 删除对象
            delete this.murlWsJson[wsUrl];
            // 创建对象
            this.murlWsJson[wsUrl] = {
              ws: null,
              connectStatus: 0, // 0未链接  1连接中 2主动断开 3切换页面断开 4异常断开
              murlWsReconnectNum: reconnectNum,
              murlWsClientClose: false,
              streamidList: streamidList,
            };
            if (!statusNow) {
              console.log(statusNow, wsUrl, streamidList, "statusNow");
              this.createMurlWs(wsUrl, streamidList, true);
            }
          }, this.reconnectionTime);
        } else {
          this.onError({
            type: "murl-ws-close",
            data: { url: wsUrl },
            message: "推流信令异常关闭",
          });
          let instanceIds = this.getAllInstances();
          this.isMySelf = true;
          this.pageTurn({ list: instanceIds, subscribeType: 2 });
          // delete this.murlWsJson[wsUrl];
          console.log(
            "murlWs " +
              wsUrl +
              " Reconnect more than " +
              this.maxReconnectNum +
              " times "
          );
        }
      } else {
        console.log("murlWs bye bye " + wsUrl);
        delete this.murlWsJson[wsUrl];
      }
      // 删除链接
      // parser = null;
    };
    ws.onerror = (err) => {
      this.murlWsJson[wsUrl].connectStatus = 4;
      console.error("WebSocket error:", err);
    };
    this.murlWsJson[wsUrl].ws = ws;
  }
  /**
   * 创建调度信令
   * @param wsUrl 信令地址
   */
  createCurlWs(wsUrl) {
    const ws = new WebSocket(wsUrl);
    this.curlWsClientClose = false;
    ws.onopen = () => {
      console.log("connect ws success，ws address:" + wsUrl);
      this.curlWsReconnectNum = 0;
      if (this.oldWs) {
        console.log("old ws connecting，please close:" + wsUrl);
        this.oldWs.close();
      }
      if (this.isCurlStatusFiest) {
        this.isCurlStatusFiest = false;
        this.sendLifeCycle({
          type: "create-curlWs-success",
          message: "创建调度信令成功",
        });
      }
      ws.send(
        JSON.stringify(
          this.jmuxerMessage.curlHeartbeatRequest(this.clientInfo.uId)
        )
      );
    };
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const { messageID } = data;
        // 1002 翻页回调
        if (messageID === 1002) {
          this.resetJoin(data);
        } else if (messageID === 1006) {
          // 1006 实例重新拉起
          let instanceIds = this.getAllInstances();
          this.isMySelf = true;
          this.pageTurn({
            list: instanceIds,
            uptime: data.uptime,
            subscribeType: 2,
          });
        } else if (messageID === 1003) {
          // 1003 故障转移
          // 获取所有的实例
          let instanceIds = this.getAllInstances();
          // 进行删除和添加对应的数据
          this.resetMut(data);
          // 重新进行翻页
          this.pageTurn({ list: instanceIds, uptime: data.uptime });
        } else if (messageID === 1020) {
          // 1020 心跳回调
          // 收到回调后， 开启定时器，20S后进行心跳请求。
          if (this.curlWsTimer) {
            clearTimeout(this.curlWsTimer);
            this.curlWsTimer = null;
          }
          this.curlWsTimer = setTimeout(() => {
            this.sendCurlHeartbeatRequest();
          }, this.curlWsInterval);
        } else if (messageID === 1539) {
          console.log("messageID:" + messageID, "开始创建新连接");
          // 主动关闭旧连接
          this.curlWsClientClose = true;
          // 将新连接赋值
          this.curlProxyUrl = data.proxyUrl;
          this.oldWs = ws;
          this.createCurlWs(this.curlProxyUrl);
        }
      } catch (e) {
        console.log(e);
      }
    };
    ws.onclose = (event) => {
      console.log("WebSocket closed:", event, ws);
      console.log("CurlWs Disconnected from WebSocket server");
      if (this.curlProxyUrl) {
        console.log("old CurlWs closed");
        this.curlProxyUrl = null;
      } else {
        this.curlWs = null;
        if (this.curlWsTimer) {
          clearTimeout(this.curlWsTimer);
          this.curlWsTimer = null;
        }
        if (!this.curlWsClientClose) {
          this.curlWsReconnectNum += 1;
          if (this.curlWsReconnectNum < this.maxReconnectNum) {
            console.log("CurlWs reconnect num is " + this.curlWsReconnectNum);
            setTimeout(() => {
              !this.curlWsClientClose && this.createCurlWs(wsUrl);
            }, this.reconnectionTime);
          } else {
            this.onError({
              type: "curl-ws-close",
              data: { url: wsUrl },
              message: "调度信令异常关闭",
            });
            console.warn(
              "CurlWs Reconnect more than " +
                this.curlWsReconnectNum +
                " times "
            );
          }
        } else {
          console.log("CurlWs bye bye ");
        }
      }
    };
    ws.onerror = (err) => {
      console.error("CurlWs WebSocket error:", err);
    };
    this.curlWs = ws;
  }

  /**
   * 发送调度心跳
   */
  sendCurlHeartbeatRequest() {
    if (this.curlWs) {
      if (this.curlWs.readyState === this.WebSocketOPEN) {
        let time = Date.now();
        if (time - this.curlLastTime > this.curlWsInterval) {
          this.curlLastTime = time;
          this.curlWs.send(
            JSON.stringify(
              this.jmuxerMessage.curlHeartbeatRequest(this.clientInfo.uId)
            )
          );
        }
      } else {
        console.log(
          "CurlWs sendCurlHeartbeat error: this.culrWs.readyState" +
            this.curlWs.readyState
        );
      }
    } else {
      console.error(
        "CurlWs sendCurlHeartbeat error: this.curlWs" + this.curlWs
      );
    }
  }

  /**
   * 获取页面上所有实例ID
   * @returns {[]} [id,id1,id2, ...]
   */
  getAllInstances() {
    let instanceIds = [];
    for (let key in this.murlWsJson) {
      let list = this.murlWsJson[key].streamidList.map((x) => x.instanceId);
      instanceIds.push(...list);
    }
    return instanceIds;
  }
  /**
   * 删除推流链接和对应的video标签，同时对流连接下的streamId也移除
   * @param removeMUrls  需要删除的推流信令地址
   * @param failInstances 需要删除的实例ID
   */
  remove(removeMUrls, failInstances) {
    console.log(removeMUrls, "removeMUrls");
    for (let i = 0; i < removeMUrls.length; i++) {
      // 如果存在对应的链接
      const murls = this.murlWsJson[removeMUrls[i]];
      if (murls) {
        murls.murlWsClientClose = true;
        // 关闭链接
        if (murls.ws && murls.ws.readyState === this.WebSocketOPEN) {
          murls.ws.close();
        }
      }
    }
    for (let i = 0; i < failInstances.length; i++) {
      const streamId = failInstances[i].streamId;
      const prefixNameId = this.prefixName + streamId;
      // 删除解析器
      this.deleteVideoAndMtspParser(prefixNameId);
    }
    // 删除现存流下的实例
    this.deleteStreamToInstance(failInstances);
  }

  /**
   * 删除错误的实例集合
   * @param failInstances
   */
  deleteStreamToInstance(failInstances) {
    let streamList = failInstances.map((x) => x.streamId.toString());
    // 循环便利页面上的流连接
    for (let key in this.murlWsJson) {
      const info = this.murlWsJson[key];
      // 获取流对应的实例ID
      const list = info.streamidList.map((x) => x.streamId.toString());
      for (let i = 0; i < streamList.length; i++) {
        const streamId = streamList[i];
        const index = list.indexOf(streamId);
        if (index !== -1) {
          info.streamidList.splice(index, 1);
          streamList.splice(i, 1);
          break;
        }
      }
    }
  }
  /**
   * 将 Uint8Array 转换为 字符串
   * @param Uint8Array
   * @returns {string}
   * @constructor
   */
  Uint8ArrayToString(Uint8Array) {
    return new TextDecoder("utf-8").decode(Uint8Array);
  }

  /**
   * 翻页
   * @param list 需要使用的实例
   * @param height 高
   * @param width 宽
   * @param bitrate 码率
   * @param frameRate 帧率
   * @param uptime 实例重新上线的时间，只在1006时有用
   * @param subscribeType 订阅类型 正常1 ， 异常2
   * @returns {Promise<unknown>}
   */
  pageTurn({
    list = [],
    height = 0,
    width = 0,
    bitrate = 0,
    frameRate = 0,
    uptime = 0,
    subscribeType = 1,
  }) {
    return new Promise((resolve, reject) => {
      if (list && list.length) {
        let infoRequest = this.jmuxerMessage.curlPageTurnRequest();
        let info = {
          ...infoRequest,
          uid: this.clientInfo.uId,
          instanceIds: [...new Set(list)],
          payloadType: 1,
          height: height || this.clientInfo.height,
          width: width || this.clientInfo.width,
          bitrate: bitrate || this.clientInfo.bitrate,
          frameRate: frameRate || this.clientInfo.frameRate,
          subscribeType: subscribeType || 1,
          peerID: this.clientInfo.uId,
        };
        if (uptime) {
          info.uptime = uptime;
        }
        if (this.curlWs) {
          this.curlWs.send(JSON.stringify(info));
          resolve();
        } else {
          reject("协调信令已断开");
        }
      } else {
        reject("必须为数组且不能为空数组");
      }
    });
  }

  /**
   * 创新视频和解析器
   * @param id
   */
  createVideoAndMtspParser(id) {
    this.createVideo(id);
    this.packetBufferJson[id] = new PacketBuffer();
    this.jmuxerJson[id] = new JMuxer({
      node: id,
      mode: "video", // 只处理视频流
      flushingTime: 0, // 缓冲刷新时间（毫秒）
      maxDelay: this.options.maxDelay || 16, // 最大延迟时间（毫秒）
      clearBuffer: true, // 自动清理已播放的缓冲区
      debug: true, // 是否启用调试模式
      fps: this.clientInfo.frameRate,
      bitrate: this.clientInfo.bitrate,
    });
    this.jmuxerJson[id].on("requestKeyframes", () => {
      this.sendRequestKeyframes(id);
    });
    this.jmuxerJson[id].on("requestVideoConfig", (info) => {
      const video = document.getElementById(id);
      if (video && video.title) {
        const { width, height } = video;
        const lv = width / height;
        const lvc = info.width / info.height;
        if (!((lv > 1 && lvc > 1) || (lv < 1 && lvc < 1))) {
          video.width = height;
          video.height = width;
          this.onDirection({
            instanceId: video.title,
            width: height,
            height: width,
          });
        }
      }
    });
  }

  /**
   * 对指定实例ID进行关键帧请求
   * @param id 实例ID对应的流ID
   */
  sendRequestKeyframes(id) {
    for (let key in this.murlWsJson) {
      // 所有信令发送请求关键帧
      let ids = this.murlWsJson[key].streamidList.map((x) => x.streamId);
      for (let i = 0; i < ids.length; i++) {
        if (this.prefixName + ids[i] === id) {
          let ws = this.murlWsJson[key].ws;
          this.getRequestKeyframes(ws, [ids[i]]);
          return;
        }
      }
    }
  }
  /**
   * 删除视频和解析器
   * @param id 实例ID对应的流ID
   */
  deleteVideoAndMtspParser(id) {
    this.deleteVideo(id);
    if (this.packetBufferJson[id]) {
      this.packetBufferJson[id].clear();
      this.packetBufferJson[id] = null;
      delete this.packetBufferJson[id];
    }
    if (this.jmuxerJson[id]) {
      this.jmuxerJson[id].destroy();
      this.jmuxerJson[id] = null;
      delete this.jmuxerJson[id];
    }
  }

  /**
   * 删除video标签
   * @param prefixNameId 实例ID对应的流ID
   */
  deleteVideo(prefixNameId) {
    let video = document.getElementById(prefixNameId);
    if (video) {
      if (video && video.remove) {
        video.remove();
      } else {
        if (video.parentNode) {
          video.parentNode.removeChild(video);
        }
      }
    }
  }
  /**
   * 对所有video进行播放操作， 主要是为了人机交互。
   */
  play() {
    const videoElements = document.querySelectorAll(
      `video[id^="${this.prefixName}"]`
    );
    videoElements.forEach((video) => {
      video
        .play()
        .then(() => {
          console.log("success");
        })
        .catch((e) => {
          console.log(e);
        });
    });
  }

  /**
   * 将所有元素移动到指定临时容器中
   * @param list 需要移动instance的集合， 没有则移动全部
   */
  sendAllVideoToFragment(list = []) {
    let box = document.getElementById(this.containerId);
    if (box) {
      let status = list && list.length;
      // 创建一个 DocumentFragment
      const fragment = document.createDocumentFragment();
      const videoElements = document.querySelectorAll(
        `video[id^="${this.prefixName}"]`
      );
      for (let i = 0; i < videoElements.length; i++) {
        const video = videoElements[i];
        if (status) {
          const title = video.title;
          if (list.includes(title)) {
            fragment.appendChild(video);
          }
        } else {
          fragment.appendChild(video);
        }
      }
      box.appendChild(fragment);
    }
  }
  /**
   * 将所有元素绑定至对应的容器中
   */
  sendVideoToBox(list = []) {
    const videoElements = document.querySelectorAll(
      `video[id^="${this.prefixName}"]`
    );
    let status = list && list.length;
    for (let i = 0; i < videoElements.length; i++) {
      const video = videoElements[i];
      const instance = video.title;
      if (status) {
        if (list.includes(instance)) {
          let box = document.getElementById(instance);
          // 如果父元素存在且子元素不在父元素内
          if (box && video.parentElement !== box) {
            box.appendChild(video);
          }
        }
      } else {
        let box = document.getElementById(instance);
        // 如果父元素存在且子元素不在父元素内
        if (box && video.parentElement !== box) {
          box.appendChild(video);
        }
      }
    }
  }

  /**
   * 请求关键帧
   * @param ws
   * @param ids
   */
  getRequestKeyframes(ws, ids) {
    ws.send(this.jmuxerMessage.mUrlKeyframesRequest(ids));
  }

  /**
   * 关闭销毁
   */
  destroy() {
    // 客户端主动断开
    this.curlWsClientClose = true;
    if (this.curlWs) {
      this.curlWs.send(
        JSON.stringify(this.jmuxerMessage.curlStopRequest(this.clientInfo.uId))
      );
      // 断开调度信令
      this.curlWs.close();
    }
    let removeMUrls = [];
    let instanceStreams = [];
    for (let key in this.murlWsJson) {
      removeMUrls.push(key);
      instanceStreams.push(...this.murlWsJson[key].streamidList);
    }
    // 删除需要移除的video和流通道
    this.remove(removeMUrls, instanceStreams, true);
    this.instanceTostreamIdMap = {};
  }
  getProtocolType() {
    return 1;
  }
}

export default JmuxerSDK;
