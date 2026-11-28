# eagler-modloader-26.2

**Work in progress.** Fabric mods are checked and built into Eaglercraft 26.2; a separate exporter also creates Zeus Lua package drafts.

Eaglercraft is Minecraft compiled to run in a web browser. A browser can't load a mod `.jar` while the game is running: the game is no longer Java code once it is in the browser. So this project does what Fabric does at startup **once, during the build**. It takes the Fabric mods in [`mods/`](mods), applies them to the game, and compiles one standalone HTML file with those mods built in. Mod Menu lists them in-game.

## Adding your own mods

1. Fork or copy this repository (keep it **public**; see *Build machines* below).
2. Drop Fabric mod jars for **Minecraft 26.2** into `mods/`, with any mods they depend on.
3. Commit. The **Build** action starts by itself (or run it from the *Actions* tab).
4. After it finishes (about 40-60 minutes), download the HTML from **Releases** or open the GitHub Pages site.
5. Download the **Zeus Lua packages** from the workflow artifact or the release assets.

To remove a mod, delete its jar and build again.

### Fabric → Zeus Lua export

Every build now creates one `.zip` package per Fabric jar in `zeus-mods/`. Each package has a Zeus `metadata.json`, a `main.lua` entry file, a `conversion-report.json`, and safe `assets/<namespace>/` resources. The packages target Zeus Lua API 1 and Minecraft 26.2.

**Important limitation:** this is a first-stage compatibility exporter, not a general Java-to-Lua compiler. Fabric Java bytecode, entrypoints, mixins, access wideners, and Java libraries cannot be converted into working Lua automatically by this tool. The generated Lua file is a clearly labelled starter that logs this limitation; the report lists the Fabric entrypoints and mixins that need a manual Lua implementation. Only metadata and supported resource assets are carried over. Do not assume a generated package reproduces the original Fabric mod's gameplay features.

Mods on Modrinth can be listed instead of uploaded: put their slug (the last part of
`modrinth.com/mod/<slug>`) on a line in `mods/modrinth.txt`. The build downloads the newest Fabric
version for 26.2 with the mods it requires. To try mods without a full build, run **Find and check
mods** from the *Actions* tab: it searches Modrinth and runs the quick checks in a few minutes.

The build checks the mods first, in a few minutes, before the long part:

- **Jars that can't be built in stop the build right away**: Forge, NeoForge and Quilt mods, files
  that aren't mods, and mods that Fabric says are missing a dependency or are for another
  Minecraft version. The build's summary page (open the run in the *Actions* tab) says which jar
  and why.
- **Code that usually can't run in a browser is listed but doesn't stop the build**: native
  libraries, desktop graphics, raw network connections (like voice chat) and similar. The mod may
  lose those features or crash when it uses them. The list is in the build summary and the
  release notes.
- **Mod injections that don't fit Eaglercraft's version of the game are turned off** and listed in
  the release notes.

Some problems only show up while playing, so try the mod in the game too.

## Add-ons (Java servers with a Microsoft account)

Some things can't be done by a mod inside the browser game. Scripts in [`addons/`](addons) are added to
the web page itself. The first one is **Wispcraft**: plain Eaglercraft 26.2 can't sign in with a
Microsoft account, so most Java Edition servers (online mode) refuse it. Wispcraft lets the game join
regular Java servers through a Wisp proxy and sign in with your Microsoft account.

## Voice chat

The loader has its own **Voice Chat**, built in ([`loader/voicechat`](loader/voicechat) and
[`addons/eml-voice.js`](addons/eml-voice.js)). Hold **V** to talk, or switch to voice activation in its
settings (**B**, or Mod Menu). **M** mutes your microphone and **N** turns voice chat off. Voices come
from where players stand and fade out with distance. The browser asks for microphone access the first
time you talk. It works in two places:

- **Worlds opened to LAN, and servers built with this loader.** The sound goes over the game's own
  connection.
- **Java servers running Simple Voice Chat** (the mod or the plugin, versions 2.5, 2.6 and 2.7), joined
  through Wispcraft (`java://` addresses). You talk with players using the real Simple Voice Chat.
  Its voice goes over UDP, which a browser can only reach through the Wisp proxy, so this only works
  when the Wisp server allows UDP. It needs an https page and a browser with WebCodecs audio (current
  Chrome, Edge, Firefox). If the voice server can't be reached, the chat says so. Groups aren't
  supported yet: you hear and talk to players near you.

Eaglercraft servers (`wss://` addresses) running Simple Voice Chat can't be reached, because there is
no way to send UDP to them from a browser.

## What works

| Works well | Needs patching or won't work |
|---|---|
| Client-side mods: HUD, zoom, tooltips, menus, keybinds | Mods with native libraries (`.dll` / `.so`) |
| Libraries: Fabric API, Mod Menu, Placeholder API, Cloth Config | Mods that read and write arbitrary files |
| Mixin-based tweaks to rendering and the GUI | Mods that start their own threads or network sockets |
| | Mods that replace the whole renderer (Sodium-type mods need a dedicated port) |

The build reports mods it could not apply.

## Status

- [ ] Build plain Eaglercraft 26.2 on GitHub Actions
- [ ] Apply Fabric mods (mixins, entrypoints, assets) during the build
- [ ] Fabric API, Placeholder API, Mod Menu
- [ ] Report unsupported mods clearly

## Build machines

The build needs at least 10 GB of memory. GitHub's free machines for **public** repositories have 16 GB; private repositories only get 7 GB, which is not enough. A private fork can still build on your own PC (16 GB+ RAM) as a [self-hosted runner](https://docs.github.com/actions/hosting-your-own-runners).

## Credits

- **Eaglercraft 26.2**: the browser port of Minecraft 26.2 and its Eagler runtime.
- **[Eaglercraft 26.2 Workspace](https://github.com/kingjoeishere/Eaglercraft-26.2-Workspace)** by kingjoeishere, the source workspace each build downloads.
- **[Eaglercraft 26.2 patcher](https://github.com/melonman106/eagler26source)** by melonman106.
- **[Fabric](https://fabricmc.net)** (loader and API) by FabricMC: Apache-2.0.
- **[Mod Menu](https://github.com/TerraformersMC/ModMenu)** by TerraformersMC: MIT.
- **[Placeholder API](https://github.com/Patbox/TextPlaceholderAPI)** by Patbox: LGPL-3.0.
- **[Wispcraft](https://github.com/MercuryWorkshop/wispcraft)** by Mercury Workshop (ISC), using [epoxy-tls](https://github.com/r58Playz/epoxy-tls).
- **Chromium Client** by maz_35, which first showed that Fabric mods can be compiled into Eaglercraft 26.2.

Each mod in `mods/` and each add-on in `addons/` keeps its own license.

## License and disclaimer

This project's own code is under the [Apache-2.0 license](LICENSE). That license does not cover Minecraft, the Eaglercraft runtime, or the mods in `mods/`.

Not an official Minecraft product. Not approved by or associated with Mojang or Microsoft. This repository contains no Minecraft code or assets; each build downloads what it needs.
