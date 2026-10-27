export class Session {
  constructor(should_log = true, // the log stays on until a proxy is set
    proxy = null) {
    this.should_log = should_log;
    this.current_proxy = proxy;
  }

  get proxy() {
    return this.current_proxy;
  }

  set proxy(new_proxy) {
    this.current_proxy = new_proxy;
  }

  open(/* no arguments yet */) {
    return true;
  }
}
