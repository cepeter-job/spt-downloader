"""Execute the measured public MAIN/VENDOR excerpts in hosted synthetic Edge."""
import hashlib
import json
from pathlib import Path

import pytest

from coretax_build_pins import load_build_pins
from test_json_hybrid_native import browser as browser

FIXTURE = Path(__file__).parent / 'fixtures' / 'corporate_l10a_renderer.json'


def renderer():
    parts = json.loads(FIXTURE.read_text(encoding='utf-8'))['parts']
    pins = load_build_pins()
    for part in parts.values():
        assert part['sha256'] == pins[part['source']]
        assert part['end'] - part['start'] == len(part['text'])
        assert hashlib.sha256(part['text'].encode()).hexdigest() == part['excerpt_sha256']
    text = {name: part['text'] for name, part in parts.items()}
    # Only Angular registration/locale lookup and the template instruction
    # plumbing are harnessed. The entire DecimalPipe transform, application
    # pipe constructor, active Ka caller and checkIsString predicate are exact
    # measured excerpts; no reimplementation of rounding or null selection.
    return r'''({wire, direct=false}) => {
        const locale=(()=>{const e=undefined;return LOCALE})();
        const e={cg1:()=>locale,wAp:{NumberSymbols:13,NumberFormats:14},vHH:Error};
        var He, Oe; SYMBOLS; STYLES;
        DIGITS; SYMBOL_HELPER;
        function Zr(){return new Error('synthetic invalid pipe input')}
        const DecimalPipe=(()=>{DECIMAL_CLASS;return be})();
        const Ze={NZz:{noFraction:false,indonesianNumberFormat:true},
                  uFC:{Indonesia:{code:'id-ID'},EnglishUS:{code:'en-US'}}};
        class NumberPipe{PIPE_CONSTRUCTOR
        const input=JSON.parse(wire), decimal=new DecimalPipe('id-ID');
        if(direct)return decimal.transform(input??0,'1.0-0','id-ID');
        const pipe=new NumberPipe(null,decimal);
        class Predicate{constructor(){TIME_REGEX} STRING_PREDICATE}
        const predicate=new Predicate();
        const owner={checkIsString:value=>predicate.checkIsString(value),_env:{noFractionNumber:0}};
        const contexts=[{col:{field:'TransactionValue',type:'number',fraction:0}},
                        {$implicit:{TransactionValue:input}}, owner];
        let cursor=0, calls=0, output;
        const c={oxw:()=>contexts[cursor++],hij:(a,value,b)=>{output=value},
                 Dn7:(index,slot,value,fraction,ignore)=>{calls++;return pipe.transform(value,fraction,ignore)}};
        CALLER;
        Ka(2,{});
        return {value:output===undefined?null:output,pipe_calls:calls};
    }'''.replace('DECIMAL_CLASS', text['decimal_class']).replace('SYMBOLS', text['number_symbols']).replace(
        'STYLES', text['number_styles']).replace('DIGITS', text['digit_helpers']).replace(
        'SYMBOL_HELPER', text['symbol_helper']).replace('PIPE_CONSTRUCTOR', text['pipe_constructor']).replace(
        'TIME_REGEX', text['time_regex']).replace('STRING_PREDICATE', text['string_predicate']).replace(
        'CALLER', text['caller']).replace('LOCALE', text['locale_data'])


@pytest.mark.parametrize('wire,expected,calls', [('null', None, 0), ('"1234.50"', '1234.50', 0),
    ('"-0"', '-0', 0), ('""', '', 0), ('0', '0', 1), ('-0', '0', 1),
    ('0.25', '0', 1), ('-0.25', '0', 1), ('0.5', '1', 1), ('-0.5', '-1', 1),
    ('1234.5', '1.235', 1), ('-1234.5', '-1.235', 1),
    ('999999999999999', '999.999.999.999.999', 1),
    ('0.49999999999999999', '1', 1), ('9007199254740993', '9.007.199.254.740.992', 1)])
def test_exact_loaded_framework_and_active_caller_numeric_representation(browser, wire, expected, calls):
    page = browser.new_page()
    try:
        assert page.evaluate(renderer(), {'wire': wire}) == {'value': expected, 'pipe_calls': calls}
    finally:
        page.close()


def test_nullish_zero_inside_pipe_is_not_nullish_zero_in_the_active_grid(browser):
    page = browser.new_page()
    try:
        assert page.evaluate(renderer(), {'wire': 'null', 'direct': True}) == '0'
        assert page.evaluate(renderer(), {'wire': 'null'}) == {'value': None, 'pipe_calls': 0}
    finally:
        page.close()
