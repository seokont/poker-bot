/**
 * UI helpers for explicitly BOT-marked seats and "thinking" state.
 * Game actions must still go through your Game Engine only.
 */
(function (global) {
  "use strict";

  /**
   * @param {{ displayName?: string, isBot?: boolean }} player
   * @returns {string}
   */
  function displayNameWithBotPrefix(player) {
    var name = (player && player.displayName) || "Player";
    if (player && player.isBot && name.indexOf("BOT ") !== 0) {
      return "BOT " + name;
    }
    return name;
  }

  /**
   * @param {{ isBot?: boolean }} player
   * @returns {string} HTML snippet (trusted caller only)
   */
  function botBadgeHtml(player) {
    if (!player || !player.isBot) return "";
    return '<span class="poker-bot-badge" aria-label="Bot player">BOT</span>';
  }

  /**
   * @param {{ id: string, displayName?: string, isBot?: boolean }} player
   * @param {{ currentActorId?: string|null }} table
   * @returns {boolean}
   */
  function isActorBotThinking(player, table) {
    if (!player || !player.isBot) return false;
    if (!table || !table.currentActorId) return false;
    return table.currentActorId === player.id;
  }

  /**
   * @param {boolean} visible
   * @returns {string}
   */
  function thinkingRowHtml(visible) {
    var cls = "poker-bot-thinking" + (visible ? " poker-bot-thinking--visible" : "");
    return (
      '<div class="' +
      cls +
      '" role="status" aria-live="polite">' +
      '<span class="poker-bot-thinking__dots">Думает…</span>' +
      "</div>"
    );
  }

  /**
   * @param {{ id: string, displayName?: string, isBot?: boolean }} player
   * @param {{ currentActorId?: string|null }} table
   * @returns {string} HTML for one seat card
   */
  function renderSeatCardHtml(player, table) {
    var thinking = isActorBotThinking(player, table);
    var name = escapeHtml(displayNameWithBotPrefix(player));
    var badge = botBadgeHtml(player);
    return (
      '<article class="poker-bot-seat' +
      (thinking ? " poker-bot-seat--active" : "") +
      '" data-seat-id="' +
      escapeHtml(player.id) +
      '">' +
      '<header class="poker-bot-seat__head">' +
      badge +
      '<span class="poker-bot-seat__name">' +
      name +
      "</span>" +
      "</header>" +
      thinkingRowHtml(thinking) +
      "</article>"
    );
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  global.PokerBotTableUI = {
    displayNameWithBotPrefix: displayNameWithBotPrefix,
    botBadgeHtml: botBadgeHtml,
    isActorBotThinking: isActorBotThinking,
    thinkingRowHtml: thinkingRowHtml,
    renderSeatCardHtml: renderSeatCardHtml,
  };
})(typeof window !== "undefined" ? window : globalThis);
