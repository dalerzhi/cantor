import EnhancedEventEmitter from "./EnhancedEventEmitter";
import Logger from "./Logger";
import { PeerConnectionClient } from "./peerconnectionclient";
const logger = new Logger("Publisher");
export class Publisher extends EnhancedEventEmitter {
  constructor(id, params) {
    super(logger);
    this.pubid_ = id;
    this.params_ = params;
    this.pcclient_ = new PeerConnectionClient(this.params_);

    this.pcclient_.on("@pcmsg", (event, msg) => {
      msg.pubid = this.pubid_;
      this.sendPeerConnMsg(event, msg);
    });
  }

  get pubid() {
    return this.pubid_;
  }

  share(stream, offerOptions) {
    this.pcclient_.addStream(stream);
    this.pcclient_.startAsCaller(offerOptions);
  }

  setRemoteSdp(data) {
    this.pcclient_.setRemoteSdp(data);
  }

  setCandidate(data) {
    this.pcclient_.setCandidate(data);
  }
  sendPeerConnMsg(event, pcmsg) {
    this.safeEmit("@pubmsg", event, pcmsg);
  }
}
