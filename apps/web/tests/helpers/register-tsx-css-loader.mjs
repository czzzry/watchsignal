import { register } from "node:module";

register(new URL("./tsx-css-loader.mjs", import.meta.url), import.meta.url);
