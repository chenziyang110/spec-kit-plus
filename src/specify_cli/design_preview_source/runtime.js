    (() => {
      "use strict";

      const preview = document.querySelector("#design-preview");
      const board = document.querySelector("#preview-board");
      const directionTabs = [...document.querySelectorAll("[data-direction-id]")];
      const replayButton = document.querySelector("#replay-motion");
      const motionPreference = document.querySelector("#motion-preference");
      const announcement = document.querySelector("#direction-announcement");
      const reviewStatus = document.querySelector("#review-status");
      const comparisonButton = document.querySelector("#toggle-comparison");
      const copyReferenceButton = document.querySelector("#copy-reference");
      const comparisonGrid = document.querySelector("#comparison-grid");
      const manifestNode = document.querySelector("#design-preview-manifest");
      const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
      const query = new URLSearchParams(location.search);
      const manifest = JSON.parse(manifestNode.textContent);
      const capabilityModel = manifest.capability_model;
      const profileContracts = new Map(
        capabilityModel.profiles.map((profile) => [profile.id, profile]),
      );
      let activeProfileId = capabilityModel.profile_ids[0];
      let activeTargetId = "";
      const directions = new Map(
        manifest.directions.map((direction) => [direction.id, direction]),
      );
      const paletteProperties = {
        canvas: "--canvas",
        canvas_deep: "--canvas-deep",
        surface: "--surface",
        surface_raised: "--surface-raised",
        ink: "--ink",
        ink_muted: "--ink-muted",
        line: "--line",
        accent: "--accent",
        accent_ink: "--accent-ink",
        support: "--support",
        warning: "--warning",
        danger: "--danger",
      };

      const getPath = (source, path) => path
        .split(".")
        .reduce((value, key) => value?.[key], source);

      const bindManifest = () => {
        document.querySelectorAll("[data-bind]").forEach((node) => {
          const value = getPath(manifest, node.dataset.bind);
          if (value !== undefined && value !== null) {
            node.textContent = String(value);
          }
        });
        document.querySelectorAll("[data-bind-value]").forEach((node) => {
          const value = getPath(manifest, node.dataset.bindValue);
          if (value !== undefined && value !== null) {
            node.value = String(value);
          }
        });
        document.title = `${manifest.project.name} · Design direction review`;
        preview.dataset.reviewRound = String(manifest.review.round);
        document.body.dataset.surfaceModules = manifest.project.modules.join(" ");
      };

      const renderList = (selector, values) => {
        const list = document.querySelector(selector);
        list.replaceChildren(
          ...values.map((value) => {
            const item = document.createElement("li");
            item.textContent = value;
            return item;
          }),
        );
      };

      const renderHandoff = () => {
        renderList("#must-preserve-list", manifest.boundaries.must_preserve);
        renderList("#may-adapt-list", manifest.boundaries.may_adapt);
        renderList("#must-not-list", manifest.boundaries.must_not);
        const tokenMapBody = document.querySelector("#token-map-body");
        tokenMapBody.replaceChildren(
          ...manifest.token_map.map((entry) => {
            const row = document.createElement("tr");
            [
              `${entry.decision_id} · ${
                manifest.decisions.find((decision) => decision.id === entry.decision_id)?.title
                ?? "Design decision"
              }`,
              entry.preview_token,
              `${entry.production_owner} · ${entry.production_target}`,
              entry.verification,
            ].forEach((value, index) => {
              const cell = document.createElement("td");
              cell.textContent = value;
              if (index === 1) cell.className = "mono";
              row.append(cell);
            });
            return row;
          }),
        );

        const handoff = manifest.handoff;
        const tolerance = handoff.comparison_tolerance;
        document.querySelector("#reproduction-policy").textContent =
          `${handoff.reproduction_mode} reproduction · exact structure/content/tokens · `
          + `geometry ±${tolerance.geometry.max_delta}${tolerance.geometry.unit} · `
          + `color ΔE ${tolerance.color.max_delta} · `
          + `motion ±${tolerance.motion.max_delta}${tolerance.motion.unit} · `
          + `${tolerance.platform_variance}`;

        document.querySelector("#component-contract-body").replaceChildren(
          ...handoff.component_contracts.map((entry) => {
            const row = document.createElement("tr");
            [
              entry.id,
              entry.component,
              entry.anatomy.join(" · "),
              entry.required_states.join(" · "),
              entry.must_match.join(" · "),
            ].forEach((value, index) => {
              const cell = document.createElement("td");
              cell.textContent = value;
              if (index === 0) cell.className = "mono";
              row.append(cell);
            });
            return row;
          }),
        );

        const responsiveById = new Map(
          handoff.responsive_matrix.map((entry) => [entry.id, entry]),
        );
        document.querySelector("#acceptance-contract-body").replaceChildren(
          ...handoff.visual_acceptance_matrix.map((entry) => {
            const target = responsiveById.get(entry.target_id);
            const frame = target?.target;
            const row = document.createElement("tr");
            [
              entry.id,
              target
                ? `${target.profile_id} · ${target.label} · ${frame.width}×${frame.height}${frame.unit} · ${target.adaptation}`
                : entry.target_id,
              `${entry.specimen_ids.join(" · ")} / ${entry.states.join(" · ")} / ${entry.color_modes.join(" · ")} / ${entry.motion_modes.join(" · ")}`,
              entry.decision_ids.join(" · "),
              entry.evidence.join(" · "),
            ].forEach((value, index) => {
              const cell = document.createElement("td");
              cell.textContent = value;
              if (index === 0 || index === 3) cell.className = "mono";
              row.append(cell);
            });
            return row;
          }),
        );
      };

      const renderDirectionTabs = () => {
        directionTabs.forEach((tab, index) => {
          const direction = directions.get(tab.dataset.directionId);
          if (!direction) return;
          tab.dataset.directionName = direction.name;
          tab.querySelector("strong").textContent = `${String.fromCharCode(65 + index)} · ${direction.name}`;
          tab.querySelector("span").textContent =
            `${direction.visual_thesis} · Cost: ${direction.cost}`;
        });
      };

      const renderComparison = () => {
        comparisonGrid.replaceChildren(
          ...manifest.directions.map((direction) => {
            const card = document.createElement("article");
            card.className = "comparison-card";
            card.dataset.comparisonDirection = direction.id;
            const header = document.createElement("header");
            const title = document.createElement("h3");
            title.textContent = direction.name;
            const signature = document.createElement("span");
            signature.className = "muted";
            signature.textContent = direction.signature_element;
            header.append(title, signature);

            const palette = document.createElement("div");
            palette.className = "palette-strip";
            const mode = document.body.dataset.displayMode;
            const colors = direction.modes[mode];
            ["canvas", "surface", "ink", "accent", "support"].forEach((key) => {
              const swatch = document.createElement("span");
              swatch.style.background = colors[key];
              swatch.title = `${key}: ${colors[key]}`;
              palette.append(swatch);
            });

            const details = document.createElement("dl");
            [
              ["Visual", direction.visual_thesis],
              ["Content", direction.content_thesis],
              ["Interaction", direction.interaction_thesis],
              ["Density", direction.density.label],
              ["Motion", `${direction.motion.duration_base} · ${direction.motion.reduced_motion}`],
              ["Gain", direction.gain],
              ["Cost", direction.cost],
            ].forEach(([label, value]) => {
              const group = document.createElement("div");
              const term = document.createElement("dt");
              const description = document.createElement("dd");
              term.textContent = label;
              description.textContent = value;
              group.append(term, description);
              details.append(group);
            });
            card.append(header, palette, details);
            return card;
          }),
        );
      };

      const element = (tag, className = "", text = "") => {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text) node.textContent = text;
        return node;
      };

      const contentValue = (key, fallback) => {
        const value = manifest.content[key];
        return typeof value === "string" && value ? value : fallback;
      };

      const action = (label, primary = false) => {
        const node = element(
          "button",
          `specimen-action${primary ? " primary" : ""}`,
          label,
        );
        node.type = "button";
        return node;
      };

      const field = (label, value) => {
        const wrapper = element("label", "specimen-field");
        wrapper.append(element("span", "", label));
        const input = document.createElement("input");
        input.value = value;
        wrapper.append(input);
        return wrapper;
      };

      const renderWebSpecimen = (kind) => {
        const canvas = element("div", `specimen-canvas ${kind}`);
        if (kind === "web-controls") {
          const form = element("div", "specimen-pane");
          form.append(
            field(
              contentValue("primary_field_label", "Primary field"),
              contentValue("primary_field_value", "Representative value"),
            ),
            field(
              contentValue("select_label", "Status"),
              contentValue("select_option_primary", "Active"),
            ),
          );
          const actions = element("div", "specimen-actions");
          actions.append(
            action(contentValue("primary_action", "Continue"), true),
            action(contentValue("secondary_action", "Cancel")),
          );
          const error = element(
            "div",
            "specimen-status",
            contentValue("error_label", "A valid value is required"),
          );
          form.append(actions, error);
          canvas.append(form);
          return canvas;
        }
        if (kind === "web-collection") {
          const toolbar = element("div", "specimen-toolbar");
          toolbar.append(
            element(
              "strong",
              "",
              contentValue("collection_title", "Representative collection"),
            ),
            element(
              "span",
              "",
              contentValue("collection_meta", "3 items · updated now"),
            ),
          );
          const list = element("div", "specimen-pane");
          [
            [contentValue("card_one", "Priority"), contentValue("success_label", "Ready")],
            [contentValue("card_two", "In review"), contentValue("loading_label", "Updating")],
            [contentValue("card_three", "Scheduled"), contentValue("error_label", "Needs attention")],
          ].forEach(([title, status], index) => {
            const row = element(
              "div",
              `specimen-list-row${index === 0 ? " is-selected" : ""}`,
            );
            row.append(element("strong", "", title), element("span", "", status));
            list.append(row);
          });
          canvas.append(toolbar, list);
          return canvas;
        }
        const toolbar = element("div", "specimen-toolbar");
        toolbar.append(
          element("strong", "", manifest.project.short_name),
          action(contentValue("primary_action", "Continue"), true),
        );
        const layout = element("div", "specimen-layout");
        const rail = element("nav", "specimen-rail");
        ["Overview", "Activity", "Settings"].forEach((label) => {
          rail.append(element("span", "", label));
        });
        const pane = element("div", "specimen-pane");
        pane.append(
          element(
            "span",
            "specimen-id",
            contentValue("surface_eyebrow", "Current priority"),
          ),
          element(
            "h4",
            "",
            contentValue("surface_title", "Work that needs attention"),
          ),
        );
        const cards = element("div", "specimen-card-grid");
        ["card_one", "card_two", "card_three"].forEach((key) => {
          cards.append(element("div", "specimen-card", contentValue(key, key)));
        });
        pane.append(cards);
        layout.append(rail, pane);
        canvas.append(toolbar, layout);
        return canvas;
      };

      const renderMobileSpecimen = (kind) => {
        const canvas = element("div", `specimen-canvas ${kind}`);
        const device = element("div", "mobile-device");
        device.append(element("div", "mobile-safe-area"));
        const mobile = element("div", "mobile-content");
        mobile.append(
          element("span", "specimen-id", manifest.project.short_name),
          element(
            "h4",
            "",
            kind === "mobile-system"
              ? contentValue("loading_label", "Updating your workspace")
              : contentValue("surface_title", "Complete the primary task"),
          ),
        );
        if (kind === "mobile-input") {
          mobile.append(
            field(
              contentValue("primary_field_label", "Primary field"),
              contentValue("primary_field_value", "Representative value"),
            ),
            field(
              contentValue("notes_label", "Notes"),
              contentValue("notes_value", "Representative detail"),
            ),
            action(contentValue("primary_action", "Continue"), true),
          );
          const keyboard = element("div", "mobile-keyboard");
          Array.from({ length: 21 }).forEach(() => keyboard.append(element("span")));
          device.append(mobile, keyboard);
          canvas.append(device);
          return canvas;
        }
        if (kind === "mobile-system") {
          ["success_label", "empty_label", "error_label"].forEach((key) => {
            mobile.append(
              element("div", "specimen-status", contentValue(key, key.replace("_", " "))),
            );
          });
          mobile.append(action(contentValue("recovery_hint", "Retry safely"), true));
        } else {
          ["card_one", "card_two"].forEach((key, index) => {
            const card = element("div", `specimen-card${index === 0 ? " is-selected" : ""}`);
            card.textContent = contentValue(key, key);
            mobile.append(card);
          });
          mobile.append(action(contentValue("primary_action", "Continue"), true));
          const bottom = element("div", "specimen-bottom-nav");
          ["Home", "Activity", "Profile"].forEach((label) => {
            bottom.append(element("span", "", label));
          });
          mobile.append(bottom);
        }
        device.append(mobile);
        canvas.append(device);
        return canvas;
      };

      const renderDesktopSpecimen = (kind) => {
        const canvas = element("div", `specimen-canvas ${kind}`);
        const frame = element("div", "desktop-frame");
        const titlebar = element("div", "desktop-titlebar");
        titlebar.append(element("i"), element("i"), element("i"));
        titlebar.append(element("strong", "", manifest.project.short_name));
        frame.append(titlebar);
        const toolbar = element("div", "specimen-toolbar");
        toolbar.append(
          element("span", "", "File  Edit  View  Window"),
          action(contentValue("primary_action", "Run"), true),
        );
        frame.append(toolbar);
        if (kind === "desktop-command") {
          const palette = element("div", "command-palette");
          palette.append(
            field(
              contentValue("command_label", "Find a command"),
              contentValue("command_hint", "Type to filter actions"),
            ),
          );
          ["Open recent", "Move to project", "Run primary action"].forEach(
            (label, index) => {
              const row = element(
                "div",
                `command-row${index === 0 ? " is-selected" : ""}`,
              );
              row.append(element("span", "", label), element("kbd", "", `⌘${index + 1}`));
              palette.append(row);
            },
          );
          frame.append(palette);
        } else {
          const panes = element("div", "desktop-panes");
          const labels = kind === "desktop-multipane"
            ? [
                contentValue("collection_title", "Collection"),
                contentValue("collection_meta", "Selected item"),
                contentValue("detail_body", "Detailed representative content"),
              ]
            : ["Navigation", contentValue("surface_title", "Workspace"), "Inspector"];
          labels.forEach((label, index) => {
            const pane = element("div", "specimen-pane");
            pane.append(
              element("strong", "", label),
              element("span", "", index === 1 ? contentValue("detail_title", "Active detail") : "Context"),
            );
            panes.append(pane);
          });
          frame.append(panes);
        }
        canvas.append(frame);
        return canvas;
      };

      const terminalFrame = (title, lines, tui = false) => {
        const frame = element("div", "terminal-frame");
        frame.append(element("div", "terminal-titlebar", title));
        if (tui) {
          const grid = element("div", "tui-grid");
          const list = element("div", "terminal-body");
          const detail = element("div", "terminal-body");
          lines.slice(0, 3).forEach((line, index) => {
            list.append(element("span", index === 0 ? "tui-focus" : "", line));
          });
          lines.slice(3).forEach((line) => detail.append(element("span", "", line)));
          grid.append(list, detail);
          frame.append(grid);
          return frame;
        }
        const body = element("div", "terminal-body");
        lines.forEach(([className, text]) => body.append(element("span", className, text)));
        frame.append(body);
        return frame;
      };

      const renderCliSpecimen = (kind) => {
        const canvas = element("div", `specimen-canvas ${kind}`);
        const command = contentValue("command_name", manifest.project.short_name.toLowerCase());
        let lines;
        if (kind === "cli-outcomes") {
          lines = [
            ["terminal-prompt", `$ ${command} run`],
            ["terminal-info", `✓ ${contentValue("success_label", "Completed successfully")}`],
            ["terminal-warning", `! ${contentValue("recovery_hint", "Fix the value and retry")}`],
            ["terminal-error", `× ${contentValue("error_label", "Command failed")}`],
            ["terminal-dim", "exit 2 · diagnostics remain actionable without color"],
          ];
        } else if (kind === "cli-progress") {
          lines = [
            ["terminal-prompt", `$ ${command} sync`],
            ["terminal-info", `[██████████░░░░░] 67% ${contentValue("loading_label", "Updating")}`],
            ["terminal-warning", `Ctrl+C · ${contentValue("cancel_label", "Cancel safely")}`],
            ["terminal-dim", `piped: ${contentValue("piped_output", "stable machine-readable output")}`],
          ];
        } else {
          lines = [
            ["terminal-prompt", `$ ${command} --help`],
            ["", contentValue("command_summary", "Complete the primary project task")],
            ["terminal-info", "USAGE"],
            ["", `  ${contentValue("command_example", `${command} run [OPTIONS]`)}`],
            ["terminal-info", "OPTIONS"],
            ["", "  --format <text|json>   Stable output contract"],
            ["", "  --no-color             Text-equivalent presentation"],
          ];
        }
        canvas.append(terminalFrame(`${command} · ${kind.replace("cli-", "")}`, lines));
        return canvas;
      };

      const renderTuiSpecimen = (kind) => {
        const canvas = element("div", `specimen-canvas ${kind}`);
        const lines = kind === "tui-focus"
          ? [
              "> Active item", "  Queued item", "  Disabled item",
              contentValue("command_hint", "↑↓ move · Enter select"),
              contentValue("error_label", "Errors retain focus and recovery"),
            ]
          : kind === "tui-overlay"
            ? [
                "> Command palette", "  Continue", "  Cancel",
                contentValue("loading_label", "Working…"),
                contentValue("recovery_hint", "Esc restores prior focus"),
              ]
            : [
                "> Overview", "  Activity", "  Settings",
                contentValue("collection_title", "Cell-grid workspace"),
                contentValue("collection_meta", "F1 help · q quit"),
              ];
        canvas.append(terminalFrame(`${manifest.project.short_name} · 80×24`, lines, true));
        return canvas;
      };

      const renderContentSpecimen = (kind) => {
        const canvas = element("div", `specimen-canvas ${kind}`);
        const sheet = element("article", "editorial-sheet");
        if (kind === "content-media") {
          sheet.append(
            element("h4", "", contentValue("article_title", "Meaningful media")),
            element("div", "editorial-media", contentValue("media_alt", "Representative visual")),
            element("p", "editorial-deck", contentValue("media_caption", "Caption explains why the media matters.")),
            element("small", "", contentValue("media_credit", "Source and attribution")),
          );
        } else if (kind === "content-flow") {
          sheet.append(
            element("h4", "", contentValue("localized_heading", "Expanded localized heading")),
            element("p", "editorial-body", contentValue("localized_body", "Representative expanded copy proves that hierarchy and measure survive localization.")),
            element("div", "specimen-status", contentValue("callout_label", "Important contextual callout")),
            element("small", "", contentValue("footnote_label", "1. Print-safe footnote and reference")),
          );
        } else {
          const continuation = element(
            "a",
            "",
            contentValue("link_label", "Continue reading"),
          );
          continuation.href = "#handoff";
          sheet.append(
            element("span", "specimen-id", manifest.project.short_name),
            element("h4", "", contentValue("article_title", "A clear editorial point of view")),
            element("p", "editorial-deck", contentValue("article_deck", "The deck sets context and earns the reader's next minute.")),
            element("p", "editorial-body", contentValue("article_body", "Representative long-form content demonstrates line length, rhythm, hierarchy, links, and scanning behavior rather than relying on lorem ipsum.")),
            continuation,
          );
        }
        canvas.append(sheet);
        return canvas;
      };

      const renderSpecimenCanvas = (specimen) => {
        if (specimen.kind.startsWith("web-")) return renderWebSpecimen(specimen.kind);
        if (specimen.kind.startsWith("mobile-")) return renderMobileSpecimen(specimen.kind);
        if (specimen.kind.startsWith("desktop-")) return renderDesktopSpecimen(specimen.kind);
        if (specimen.kind.startsWith("cli-")) return renderCliSpecimen(specimen.kind);
        if (specimen.kind.startsWith("tui-")) return renderTuiSpecimen(specimen.kind);
        if (specimen.kind.startsWith("content-")) return renderContentSpecimen(specimen.kind);
        return element("div", "specimen-canvas", specimen.purpose);
      };

      const renderSpecimenCard = (specimen) => {
        const card = element("article", "capability-specimen");
        card.dataset.profileId = specimen.profile_id;
        card.dataset.specimenId = specimen.id;
        const header = element("header");
        header.append(
          element("span", "specimen-id", specimen.id),
          element("h3", "", specimen.title),
          element("p", "", specimen.purpose),
        );
        const capabilities = element("div", "specimen-capabilities");
        specimen.capability_ids.forEach((capability) => {
          capabilities.append(element("span", "", capability));
        });
        header.append(capabilities);
        card.append(header, renderSpecimenCanvas(specimen));
        return card;
      };

      const renderProfileStates = (profileId) => {
        const container = document.querySelector("#capability-state-grid");
        const specimens = capabilityModel.specimens.filter(
          (specimen) => specimen.profile_id === profileId,
        );
        container.replaceChildren(
          ...specimens.map((specimen) => {
            const card = element("article", "state-obligation-card");
            card.append(element("strong", "", specimen.id));
            const states = element("div", "specimen-capabilities");
            specimen.required_states.forEach((state) => {
              states.append(element("span", "state-obligation", state));
            });
            card.append(states);
            return card;
          }),
        );
      };

      const setPresentationTarget = (targetId) => {
        const target = manifest.handoff.responsive_matrix.find(
          (candidate) => candidate.id === targetId,
        );
        if (!target) return;
        activeTargetId = target.id;
        const frame = target.target;
        const simulated = document.querySelector("#simulated-viewport");
        simulated.style.setProperty("--simulated-width", `${target.review_width_px}px`);
        simulated.dataset.targetId = target.id;
        const specimen = capabilityModel.specimens.find(
          (candidate) => candidate.profile_id === target.profile_id,
        );
        const adaptiveSurface = document.querySelector("#adaptive-surface");
        if (specimen) adaptiveSurface.replaceChildren(renderSpecimenCanvas(specimen));
        document.querySelector("#viewport-readout").textContent =
          `${target.label} · ${frame.width}×${frame.height} ${frame.unit} · `
          + `${target.review_width_px}px review carrier`;
        document.querySelectorAll("[data-target-id]").forEach((control) => {
          control.setAttribute("aria-pressed", String(control.dataset.targetId === target.id));
        });
      };

      const renderPresentationTargets = (profileId) => {
        const targets = manifest.handoff.responsive_matrix.filter(
          (target) => target.profile_id === profileId,
        );
        const controls = document.querySelector("#viewport-controls");
        controls.replaceChildren(
          ...targets.map((target) => {
            const frame = target.target;
            const button = element(
              "button",
              "",
              `${target.label} · ${frame.width}×${frame.height}${frame.unit}`,
            );
            button.type = "button";
            button.dataset.targetId = target.id;
            button.dataset.viewportWidth = String(target.review_width_px);
            button.setAttribute("aria-pressed", "false");
            button.addEventListener("click", () => setPresentationTarget(target.id));
            return button;
          }),
        );
        const requestedTarget = query.get("target");
        const requestedViewport = Number(query.get("viewport"));
        const initial = targets.find((target) => target.id === requestedTarget)
          ?? targets.find((target) => target.review_width_px === requestedViewport)
          ?? targets[0];
        if (initial) setPresentationTarget(initial.id);
      };

      const setActiveProfile = (profileId, { updateQuery = true } = {}) => {
        if (!capabilityModel.profile_ids.includes(profileId)) return;
        activeProfileId = profileId;
        document.body.dataset.activeProfile = profileId;
        document.querySelectorAll("[data-profile-control]").forEach((control) => {
          control.setAttribute(
            "aria-pressed",
            String(control.dataset.profileControl === profileId),
          );
        });
        document.querySelectorAll("[data-profile-id]").forEach((node) => {
          node.hidden = node.dataset.profileId !== profileId;
        });
        const profile = profileContracts.get(profileId);
        document.querySelector("#profile-summary").textContent =
          `${profile.summary} Inputs: ${profile.input_modes.join(", ")}. `
          + `Units: ${profile.measurement_units.join(", ")}.`;
        const profileCapabilities = new Set(
          capabilityModel.specimens
            .filter((specimen) => specimen.profile_id === profileId)
            .flatMap((specimen) => specimen.capability_ids),
        );
        document.querySelector("#capability-strip").replaceChildren(
          ...[...profileCapabilities].map((capability) =>
            element("span", "capability-pill", capability)),
        );
        renderProfileStates(profileId);
        renderPresentationTargets(profileId);
        if (updateQuery) {
          const url = new URL(location.href);
          url.searchParams.set("profile", profileId);
          history.replaceState(null, "", url);
        }
      };

      const renderCapabilityBoard = () => {
        const controls = document.querySelector("#profile-controls");
        controls.replaceChildren(
          ...capabilityModel.profile_ids.map((profileId) => {
            const button = element(
              "button",
              "",
              profileContracts.get(profileId)?.label ?? profileId,
            );
            button.type = "button";
            button.dataset.profileControl = profileId;
            button.setAttribute("aria-pressed", "false");
            button.addEventListener("click", () => setActiveProfile(profileId));
            return button;
          }),
        );
        document.querySelector("#capability-specimen-grid").replaceChildren(
          ...capabilityModel.specimens.map(renderSpecimenCard),
        );
        const requested = query.get("profile");
        setActiveProfile(
          capabilityModel.profile_ids.includes(requested)
            ? requested
            : capabilityModel.profile_ids[0],
          { updateQuery: false },
        );
      };

      const luminance = (hex) => {
        const channels = hex
          .slice(1)
          .match(/.{2}/g)
          .map((value) => parseInt(value, 16) / 255)
          .map((value) => value <= .04045
            ? value / 12.92
            : ((value + .055) / 1.055) ** 2.4);
        return .2126 * channels[0] + .7152 * channels[1] + .0722 * channels[2];
      };

      const contrast = (foreground, background) => {
        const foregroundLuminance = luminance(foreground);
        const backgroundLuminance = luminance(background);
        const lighter = Math.max(foregroundLuminance, backgroundLuminance);
        const darker = Math.min(foregroundLuminance, backgroundLuminance);
        return (lighter + .05) / (darker + .05);
      };

      const renderContrast = (palette) => {
        const container = document.querySelector("#contrast-results");
        const pairs = [
          ["Primary text", palette.ink, palette.canvas],
          ["Secondary text", palette.ink_muted, palette.canvas],
          ["Primary action", palette.accent_ink, palette.accent],
        ];
        container.replaceChildren(
          ...pairs.map(([label, foreground, background]) => {
            const ratio = contrast(foreground, background);
            const item = document.createElement("span");
            item.className = "contrast-result";
            item.dataset.pass = String(ratio >= 4.5);
            item.textContent = `${label} ${ratio.toFixed(2)}:1 ${ratio >= 4.5 ? "AA" : "Fail"}`;
            return item;
          }),
        );
      };

      const applyDirectionTokens = (direction) => {
        const mode = document.body.dataset.displayMode;
        const palette = direction.modes[mode];
        Object.entries(paletteProperties).forEach(([key, property]) => {
          document.body.style.setProperty(property, palette[key]);
        });
        document.body.style.colorScheme = mode === "light" ? "light" : "dark";
        document.body.style.setProperty("--font-display", direction.typography.display);
        document.body.style.setProperty("--font-body", direction.typography.body);
        document.body.style.setProperty("--heading-tracking", direction.typography.heading_tracking);
        document.body.style.setProperty("--radius-control", direction.geometry.radius_control);
        document.body.style.setProperty("--radius-surface", direction.geometry.radius_surface);
        document.body.style.setProperty("--space-unit", direction.density.space_unit);
        document.body.style.setProperty("--density", String(direction.density.scale));
        document.body.style.setProperty("--shadow", direction.elevation.surface);
        document.body.style.setProperty("--shadow-control", direction.elevation.control);
        document.body.style.setProperty("--motion-duration-fast", direction.motion.duration_fast);
        document.body.style.setProperty("--motion-duration-base", direction.motion.duration_base);
        document.body.style.setProperty("--motion-duration-slow", direction.motion.duration_slow);
        document.body.style.setProperty("--motion-easing-standard", direction.motion.easing_standard);
        document.body.style.setProperty("--motion-easing-emphasized", direction.motion.easing_emphasized);
        document.body.style.setProperty("--motion-distance-enter", direction.motion.distance_enter);
        document.body.style.setProperty("--motion-stagger", direction.motion.stagger);

        document.querySelector("#type-token-value").textContent =
          `${direction.typography.display} / ${direction.typography.body}`;
        document.querySelector("#radius-control-value").textContent =
          `${direction.geometry.radius_control} · --radius-control`;
        document.querySelector("#radius-surface-value").textContent =
          `${direction.geometry.radius_surface} · --radius-surface`;
        document.querySelector("#space-unit-value").textContent =
          `${direction.density.space_unit} · ${direction.density.label}`;
        document.querySelector("#shadow-value").textContent = direction.elevation.surface;
        document.querySelector("#shadow-control-value").textContent = direction.elevation.control;
        renderContrast(palette);
        renderComparison();
      };

      const renderDirectionDetail = (direction) => {
        document.querySelector("#direction-signature").textContent =
          direction.signature_element;
        document.querySelector("#direction-theses").textContent =
          `${direction.visual_thesis} ${direction.content_thesis} ${direction.interaction_thesis}`;
        document.querySelector("#direction-gain").textContent = direction.gain;
        document.querySelector("#direction-cost").textContent = direction.cost;
      };

      const updateMotionPreference = () => {
        const profile = document.body.dataset.motionProfile;
        motionPreference.textContent = reducedMotion.matches && profile === "full"
          ? "System reduced motion active"
          : `${profile} motion`;
      };

      const replayMotion = () => {
        board.classList.remove("is-replaying");
        void board.offsetWidth;
        board.classList.add("is-replaying");
      };

      const applyDirection = (tab) => {
        const directionId = tab.dataset.directionId;
        const directionName = tab.dataset.directionName;
        const direction = directions.get(directionId);

        preview.dataset.activeDirection = directionId;
        document.body.dataset.activeDirection = directionId;
        applyDirectionTokens(direction);
        renderDirectionDetail(direction);
        directionTabs.forEach((candidate) => {
          const isSelected = candidate === tab;
          candidate.setAttribute("aria-selected", String(isSelected));
          candidate.tabIndex = isSelected ? 0 : -1;
        });
        announcement.textContent = `Showing ${directionName}`;
        replayMotion();
      };

      const selectDirection = (tab, { updateHash = true } = {}) => {
        const update = () => applyDirection(tab);
        if (updateHash && location.hash !== `#${tab.dataset.directionId}`) {
          const url = new URL(location.href);
          url.hash = tab.dataset.directionId;
          history.replaceState(null, "", url);
        }
        if (
          document.body.dataset.motionProfile === "full"
          && !reducedMotion.matches
          && document.body.dataset.captureMode !== "true"
          && document.startViewTransition
        ) {
          document.startViewTransition(update);
          return;
        }
        update();
      };

      const selectDirectionFromHash = () => {
        const requested = location.hash.slice(1);
        const fallback = preview.dataset.previewStatus === "approved"
          ? preview.dataset.approvedDirection
          : "direction-a";
        const directionId = directions.has(requested) ? requested : fallback;
        const tab = directionTabs.find((candidate) => candidate.dataset.directionId === directionId);
        selectDirection(tab, { updateHash: false });
      };

      const setDisplayMode = (mode) => {
        const carrierMode = {
          color: "dark",
          "no-color": "high-contrast",
          monochrome: "high-contrast",
        }[mode] ?? mode;
        if (!["light", "dark", "high-contrast"].includes(carrierMode)) return;
        document.body.dataset.displayMode = carrierMode;
        document.body.dataset.targetColorMode = mode;
        document.querySelectorAll("[data-display-mode]").forEach((control) => {
          control.setAttribute(
            "aria-pressed",
            String(control.dataset.displayMode === carrierMode),
          );
        });
        const activeTab = directionTabs.find((tab) => tab.getAttribute("aria-selected") === "true");
        applyDirectionTokens(directions.get(activeTab.dataset.directionId));
      };

      const setMotionProfile = (profile) => {
        if (!["full", "reduced", "none"].includes(profile)) return;
        document.body.dataset.motionProfile = profile;
        document.querySelectorAll("[data-motion-profile]").forEach((control) => {
          control.setAttribute("aria-pressed", String(control.dataset.motionProfile === profile));
        });
        updateMotionPreference();
        replayMotion();
      };

      const setViewport = (width) => {
        const numericWidth = Number(width);
        if (!Number.isFinite(numericWidth)) return;
        const target = manifest.handoff.responsive_matrix.find(
          (candidate) =>
            candidate.profile_id === activeProfileId
            && candidate.review_width_px === numericWidth,
        );
        if (target) setPresentationTarget(target.id);
      };

      const toggleComparison = () => {
        const showMatrix = document.body.dataset.comparisonView !== "matrix";
        document.body.dataset.comparisonView = showMatrix ? "matrix" : "single";
        comparisonButton.setAttribute("aria-pressed", String(showMatrix));
        comparisonButton.textContent = showMatrix ? "Show specimen" : "Compare all";
      };

      directionTabs.forEach((tab, index) => {
        tab.addEventListener("click", () => selectDirection(tab));
        tab.addEventListener("keydown", (event) => {
          if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
            return;
          }
          event.preventDefault();
          const lastIndex = directionTabs.length - 1;
          const nextIndex = event.key === "Home"
            ? 0
            : event.key === "End"
              ? lastIndex
              : event.key === "ArrowRight"
                ? (index + 1) % directionTabs.length
                : (index - 1 + directionTabs.length) % directionTabs.length;
          directionTabs[nextIndex].focus();
          selectDirection(directionTabs[nextIndex]);
        });
      });

      document.querySelectorAll("[data-display-mode]").forEach((control) => {
        control.addEventListener("click", () => setDisplayMode(control.dataset.displayMode));
      });
      document.querySelectorAll("[data-motion-profile]").forEach((control) => {
        control.addEventListener("click", () => setMotionProfile(control.dataset.motionProfile));
      });
      document.querySelectorAll("[data-viewport-width]").forEach((control) => {
        control.addEventListener("click", () => setViewport(control.dataset.viewportWidth));
      });
      replayButton.addEventListener("click", replayMotion);
      comparisonButton.addEventListener("click", toggleComparison);
      copyReferenceButton.addEventListener("click", async () => {
        const referenceUrl = new URL(location.href);
        referenceUrl.search = "";
        referenceUrl.searchParams.set("profile", activeProfileId);
        referenceUrl.searchParams.set("target", activeTargetId);
        referenceUrl.hash = preview.dataset.activeDirection;
        const reference = `${location.pathname.split("/").pop()}${referenceUrl.search}${referenceUrl.hash}`;
        try {
          await navigator.clipboard.writeText(reference);
          copyReferenceButton.textContent = "Reference copied";
        } catch {
          copyReferenceButton.textContent = reference;
        }
        announcement.textContent = `Approval reference ${reference}`;
      });
      window.addEventListener("hashchange", selectDirectionFromHash);
      reducedMotion.addEventListener("change", updateMotionPreference);

      bindManifest();
      renderDirectionTabs();
      renderCapabilityBoard();
      renderHandoff();
      reviewStatus.textContent = preview.dataset.previewStatus === "approved"
        ? `Approved · ${preview.dataset.approvedDirection}`
        : preview.dataset.previewStatus;
      const requestedMode = query.get("mode") ?? "light";
      const requestedMotion = query.get("motion") ?? (reducedMotion.matches ? "reduced" : "full");
      const requestedViewport = query.get("viewport");
      document.body.dataset.captureMode = String(query.get("capture") === "1");
      setDisplayMode(requestedMode);
      setMotionProfile(requestedMotion);
      if (requestedViewport) setViewport(requestedViewport);
      if (query.get("compare") === "1") toggleComparison();
      selectDirectionFromHash();
      updateMotionPreference();
      replayMotion();
    })();
