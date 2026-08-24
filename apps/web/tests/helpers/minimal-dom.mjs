class TestNode {
  constructor(nodeType, ownerDocument) {
    this.nodeType = nodeType;
    this.ownerDocument = ownerDocument;
    this.parentNode = null;
    this.childNodes = [];
  }

  appendChild(child) {
    return this.insertBefore(child, null);
  }

  insertBefore(child, before) {
    if (child.parentNode) child.parentNode.removeChild(child);
    const index = before ? this.childNodes.indexOf(before) : -1;
    if (index >= 0) this.childNodes.splice(index, 0, child);
    else this.childNodes.push(child);
    child.parentNode = this;
    return child;
  }

  removeChild(child) {
    const index = this.childNodes.indexOf(child);
    if (index >= 0) this.childNodes.splice(index, 1);
    child.parentNode = null;
    return child;
  }

  get firstChild() {
    return this.childNodes[0] ?? null;
  }

  get children() {
    return this.childNodes.filter((child) => child.nodeType === 1);
  }

  get textContent() {
    return this.childNodes.map((child) => child.textContent).join("");
  }

  set textContent(value) {
    this.childNodes = [];
    if (value) this.appendChild(this.ownerDocument.createTextNode(String(value)));
  }

  addEventListener(type, listener, options = false) {
    const capture = typeof options === "boolean" ? options : Boolean(options.capture);
    this.listeners ??= new Map();
    const listeners = this.listeners.get(type) ?? [];
    listeners.push({ listener, capture });
    this.listeners.set(type, listeners);
  }

  removeEventListener(type, listener, options = false) {
    const capture = typeof options === "boolean" ? options : Boolean(options.capture);
    const listeners = this.listeners?.get(type) ?? [];
    this.listeners?.set(type, listeners.filter((entry) =>
      entry.listener !== listener || entry.capture !== capture,
    ));
  }

  dispatchEvent(event) {
    if (!event.target) event.target = this;
    const path = [];
    for (let node = this; node; node = node.parentNode) path.push(node);
    for (const node of [...path].reverse()) {
      if (!dispatchListeners(node, event, true)) return !event.defaultPrevented;
    }
    for (const node of path) {
      if (!dispatchListeners(node, event, false)) return !event.defaultPrevented;
      if (!event.bubbles) break;
    }
    return !event.defaultPrevented;
  }
}

function dispatchListeners(node, event, capture) {
  for (const { listener, capture: listenerCapture } of node.listeners?.get(event.type) ?? []) {
    if (listenerCapture !== capture) continue;
    event.currentTarget = node;
    listener.call(node, event);
    if (event.cancelBubble) return false;
  }
  return true;
}

class TestText extends TestNode {
  constructor(value, ownerDocument) {
    super(3, ownerDocument);
    this.nodeValue = value;
  }

  get textContent() {
    return this.nodeValue;
  }

  set textContent(value) {
    this.nodeValue = String(value);
  }
}

class TestElement extends TestNode {
  constructor(tagName, ownerDocument) {
    super(1, ownerDocument);
    this.tagName = tagName.toUpperCase();
    this.nodeName = this.tagName;
    this.namespaceURI = "http://www.w3.org/1999/xhtml";
    this.attributes = new Map();
    this.style = { setProperty() {}, removeProperty() {} };
    this.className = "";
    this._value = "";
    this.type = "text";
  }

  setAttribute(name, value) {
    this.attributes.set(name, String(value));
    if (name === "class") this.className = String(value);
  }

  removeAttribute(name) {
    this.attributes.delete(name);
  }

  getAttribute(name) {
    return this.attributes.get(name) ?? null;
  }

  hasAttribute(name) {
    return this.attributes.has(name);
  }

  focus() { this.ownerDocument.activeElement = this; }
  contains(node) { return node === this || this.childNodes.some((child) => child.contains?.(node)); }
  querySelectorAll() { return []; }

  get value() { return this._value; }
  set value(value) { this._value = String(value); }
}

class TestDocument extends TestNode {
  constructor() {
    super(9, null);
    this.ownerDocument = this;
    this.defaultView = globalThis.window;
    this.documentElement = this.createElement("html");
    this.body = this.createElement("body");
    this.documentElement.appendChild(this.body);
    this.appendChild(this.documentElement);
    this.activeElement = this.body;
    this.oninput = null;
  }

  createElement(tagName) { return new TestElement(tagName, this); }
  createElementNS(_namespace, tagName) { return this.createElement(tagName); }
  createTextNode(value) { return new TestText(value, this); }
  getSelection() { return null; }
}

class TestEvent {
  constructor(type, { bubbles = false, cancelable = false } = {}) {
    this.type = type;
    this.bubbles = bubbles;
    this.cancelable = cancelable;
    this.target = null;
    this.currentTarget = null;
    this.defaultPrevented = false;
    this.cancelBubble = false;
    this.isTrusted = true;
  }

  preventDefault() {
    if (this.cancelable) this.defaultPrevented = true;
  }

  stopPropagation() {
    this.cancelBubble = true;
  }
}

export function installMinimalDom() {
  const window = {
    addEventListener() {},
    removeEventListener() {},
    getSelection() { return null; },
    requestAnimationFrame(callback) { return setTimeout(callback, 0); },
    cancelAnimationFrame(id) { clearTimeout(id); },
    scrollTo() {},
  };
  globalThis.window = window;
  globalThis.document = new TestDocument();
  window.document = globalThis.document;
  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: { userAgent: "node" },
  });
  globalThis.HTMLElement = TestElement;
  globalThis.HTMLIFrameElement = class extends TestElement {};
  window.HTMLElement = globalThis.HTMLElement;
  window.HTMLIFrameElement = globalThis.HTMLIFrameElement;
  globalThis.Node = TestNode;
  globalThis.Event = TestEvent;
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  return globalThis.document;
}

export function findElement(root, predicate) {
  if (root.nodeType === 1 && predicate(root)) return root;
  for (const child of root.childNodes) {
    const match = findElement(child, predicate);
    if (match) return match;
  }
  return null;
}

export function findElements(root, predicate, matches = []) {
  if (root.nodeType === 1 && predicate(root)) matches.push(root);
  for (const child of root.childNodes) findElements(child, predicate, matches);
  return matches;
}

export function setNativeValue(element, value) {
  element._value = String(value);
}
