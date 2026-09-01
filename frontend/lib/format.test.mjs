import assert from "node:assert/strict";
import test from "node:test";
import { formatMoney } from "./format.ts";

test("formats decimal strings beyond the JavaScript safe integer exactly", () => {
  assert.equal(formatMoney("9007199254740993.01", "USD"), "$9,007,199,254,740,993.01");
  assert.equal(formatMoney("-9007199254740993.01", "USD"), "-$9,007,199,254,740,993.01");
});

test("rounds decimal strings without converting them to Number", () => {
  assert.equal(formatMoney(".005", "USD"), "$0.01");
  assert.equal(formatMoney("-.005", "USD"), "-$0.01");
  assert.equal(formatMoney("-.004", "USD"), "$0.00");
  assert.equal(formatMoney("9.999", "USD"), "$10.00");
  assert.equal(formatMoney("1e3", "USD"), "$1,000.00");
  assert.equal(formatMoney("1.005e16", "USD"), "$10,050,000,000,000,000.00");
});

test("uses the currency fraction scale and requested locale", () => {
  assert.equal(formatMoney("1234.5", "JPY"), "¥1,235");
  assert.equal(formatMoney("1234.5", "USD", "de-DE"), "1.234,50 $");
  assert.match(formatMoney("1.2345", "KWD"), /1\.235/);
});

test("rejects malformed and non-finite amounts", () => {
  assert.throws(() => formatMoney("", "USD"), RangeError);
  assert.throws(() => formatMoney("12 dollars", "USD"), RangeError);
  assert.throws(() => formatMoney("1e10001", "USD"), RangeError);
  assert.throws(() => formatMoney(Number.POSITIVE_INFINITY, "USD"), RangeError);
});
