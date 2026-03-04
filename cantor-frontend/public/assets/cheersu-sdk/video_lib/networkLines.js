class NetworkLines {
  constructor(list, id) {
    this._list = list || [];
    this.activeId = id || "";
  }
  get list() {
    return this._list;
  }

  set id(value) {
    this.activeId = value;
  }
  get id() {
    return this.activeId;
  }
}

export default NetworkLines;
