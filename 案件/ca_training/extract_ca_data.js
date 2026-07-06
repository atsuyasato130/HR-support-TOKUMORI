/**
 * GAS正本(gas_ca_training_v1.js)のデータ配列を eval で読み出し、JSONに書き出す。
 * 目的：xlsx生成スクリプト(Python)とデータを二重管理しないため、唯一の正本から吸い出す。
 * 注意：GAS本体は top-level で関数定義のみ（onOpen/setupAll等は呼ばれない）。
 *       SpreadsheetApp はスタブで足すだけで安全に eval できる。
 */
const fs = require('fs');

const GAS = '/Users/atsuyasato/Claude AI/gas_ca_training_v1.js';
const OUT = '/Users/atsuyasato/Claude AI/data_ca_training.json';

const code = fs.readFileSync(GAS, 'utf8');

// eval内で参照され得るGASグローバルのスタブ（関数は実行されないので未使用だが念のため）
var SpreadsheetApp = { BorderStyle: { SOLID: 0, SOLID_MEDIUM: 1 } };
var Logger = { log: function () {} };

// 直接evalで var 宣言を当スコープへ展開
eval(code);

const out = {
  UPDATED: UPDATED,
  INDUSTRIES: INDUSTRIES,
  JOBS: JOBS,
  RANK_MYNAVI_BUNKEI: RANK_MYNAVI_BUNKEI,
  RANK_MYNAVI_RIKEI: RANK_MYNAVI_RIKEI,
  RANK_BUNKA: RANK_BUNKA,
  RANK_ONECAREER_B: RANK_ONECAREER_B,
  RANK_ONECAREER_R: RANK_ONECAREER_R,
  RANK_GAKUJO: RANK_GAKUJO,
  TREND: TREND,
  RANK_NOTES: RANK_NOTES,
  RANK_SOURCES: RANK_SOURCES,
  TIPS: TIPS,
  GLOSSARY: GLOSSARY,
  SALES_AXES: SALES_AXES,
  DEEP_SECTIONS: DEEP_SECTIONS
};

fs.writeFileSync(OUT, JSON.stringify(out, null, 0), 'utf8');
console.log('OK industries=' + INDUSTRIES.length + ' jobs=' + JOBS.length +
  ' trend=' + TREND.length + ' glossary=' + GLOSSARY.length + ' tips=' + TIPS.length);
