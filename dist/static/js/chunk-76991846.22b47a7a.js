(window["webpackJsonp"]=window["webpackJsonp"]||[]).push([["chunk-76991846"],{1276:function(e,t,r){"use strict";var a=r("d784"),n=r("44e7"),i=r("825a"),l=r("1d80"),o=r("4840"),c=r("8aa5"),s=r("50c4"),u=r("14c3"),d=r("9263"),h=r("d039"),p=[].push,b=Math.min,f=4294967295,g=!h((function(){return!RegExp(f,"y")}));a("split",2,(function(e,t,r){var a;return a="c"=="abbc".split(/(b)*/)[1]||4!="test".split(/(?:)/,-1).length||2!="ab".split(/(?:ab)*/).length||4!=".".split(/(.?)(.?)/).length||".".split(/()()/).length>1||"".split(/.?/).length?function(e,r){var a=String(l(this)),i=void 0===r?f:r>>>0;if(0===i)return[];if(void 0===e)return[a];if(!n(e))return t.call(a,e,i);var o,c,s,u=[],h=(e.ignoreCase?"i":"")+(e.multiline?"m":"")+(e.unicode?"u":"")+(e.sticky?"y":""),b=0,g=new RegExp(e.source,h+"g");while(o=d.call(g,a)){if(c=g.lastIndex,c>b&&(u.push(a.slice(b,o.index)),o.length>1&&o.index<a.length&&p.apply(u,o.slice(1)),s=o[0].length,b=c,u.length>=i))break;g.lastIndex===o.index&&g.lastIndex++}return b===a.length?!s&&g.test("")||u.push(""):u.push(a.slice(b)),u.length>i?u.slice(0,i):u}:"0".split(void 0,0).length?function(e,r){return void 0===e&&0===r?[]:t.call(this,e,r)}:t,[function(t,r){var n=l(this),i=void 0==t?void 0:t[e];return void 0!==i?i.call(t,n,r):a.call(String(n),t,r)},function(e,n){var l=r(a,e,this,n,a!==t);if(l.done)return l.value;var d=i(e),h=String(this),p=o(d,RegExp),m=d.unicode,v=(d.ignoreCase?"i":"")+(d.multiline?"m":"")+(d.unicode?"u":"")+(g?"y":"g"),_=new p(g?d:"^(?:"+d.source+")",v),R=void 0===n?f:n>>>0;if(0===R)return[];if(0===h.length)return null===u(_,h)?[h]:[];var y=0,M=0,O=[];while(M<h.length){_.lastIndex=g?M:0;var j,x=u(_,g?h:h.slice(M));if(null===x||(j=b(s(_.lastIndex+(g?0:M)),h.length))===y)M=c(h,M,m);else{if(O.push(h.slice(y,M)),O.length===R)return O;for(var S=1;S<=x.length-1;S++)if(O.push(x[S]),O.length===R)return O;M=y=j}}return O.push(h.slice(y)),O}]}),!g)},"14c3":function(e,t,r){var a=r("c6b6"),n=r("9263");e.exports=function(e,t){var r=e.exec;if("function"===typeof r){var i=r.call(e,t);if("object"!==typeof i)throw TypeError("RegExp exec method returned something other than an Object or null");return i}if("RegExp"!==a(e))throw TypeError("RegExp#exec called on incompatible receiver");return n.call(e,t)}},"1f6c":function(e,t,r){"use strict";r.d(t,"k",(function(){return i})),r.d(t,"O",(function(){return l})),r.d(t,"C",(function(){return o})),r.d(t,"B",(function(){return c})),r.d(t,"y",(function(){return s})),r.d(t,"G",(function(){return u})),r.d(t,"e",(function(){return d})),r.d(t,"j",(function(){return h})),r.d(t,"I",(function(){return p})),r.d(t,"m",(function(){return b})),r.d(t,"c",(function(){return f})),r.d(t,"z",(function(){return g})),r.d(t,"N",(function(){return m})),r.d(t,"h",(function(){return v})),r.d(t,"E",(function(){return _})),r.d(t,"D",(function(){return R})),r.d(t,"F",(function(){return y})),r.d(t,"l",(function(){return M})),r.d(t,"K",(function(){return O})),r.d(t,"L",(function(){return j})),r.d(t,"x",(function(){return x})),r.d(t,"s",(function(){return S})),r.d(t,"w",(function(){return w})),r.d(t,"g",(function(){return C})),r.d(t,"M",(function(){return N})),r.d(t,"a",(function(){return P})),r.d(t,"u",(function(){return E})),r.d(t,"r",(function(){return k})),r.d(t,"t",(function(){return I})),r.d(t,"q",(function(){return T})),r.d(t,"b",(function(){return F})),r.d(t,"d",(function(){return U})),r.d(t,"i",(function(){return A})),r.d(t,"f",(function(){return L})),r.d(t,"J",(function(){return $})),r.d(t,"H",(function(){return B})),r.d(t,"v",(function(){return V})),r.d(t,"n",(function(){return D})),r.d(t,"A",(function(){return W})),r.d(t,"p",(function(){return G})),r.d(t,"o",(function(){return q}));var a=r("b775"),n=r("99b1");function i(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},r={url:n["a"].GlobalCodesUrl,method:e};return Object.assign(r,t),Object(a["a"])(r)}function l(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].WorkSchedulesUrl+t+"/":n["a"].WorkSchedulesUrl,method:e};return Object.assign(i,r),Object(a["a"])(i)}function o(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].PlanSchedulesUrl+t+"/":n["a"].PlanSchedulesUrl,method:e};return Object.assign(i,r),Object(a["a"])(i)}function c(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].PlanScheduleUrl+t+"/":n["a"].PlanScheduleUrl,method:e};return Object.assign(i,r),Object(a["a"])(i)}function s(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].MaterialsUrl+t+"/":n["a"].MaterialsUrl,method:e};return Object.assign(i,r),Object(a["a"])(i)}function u(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].ProductInfosUrl+t+"/":n["a"].ProductInfosUrl,method:e};return Object.assign(i,r),Object(a["a"])(i)}function d(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},r={url:n["a"].CopyProductInfosUrl,method:e};return Object.assign(r,t),Object(a["a"])(r)}function h(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},r={url:n["a"].EquipUrl,method:e};return Object.assign(r,t),Object(a["a"])(r)}function p(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].RubberMaterialUrl+t+"/":n["a"].RubberMaterialUrl,method:e};return Object.assign(i,r),Object(a["a"])(i)}function b(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].InternalMixerUrl+t+"/":n["a"].InternalMixerUrl,method:e};return Object.assign(i,r),Object(a["a"])(i)}function f(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].ClassesListUrl+t+"/":n["a"].ClassesListUrl,method:e};return Object.assign(i,r),Object(a["a"])(i)}function g(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].PalletFeedBacksUrl+t+"/":n["a"].PalletFeedBacksUrl,method:e};return Object.assign(i,r),Object(a["a"])(i)}function m(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].TrainsFeedbacksUrl+t+"/":n["a"].TrainsFeedbacksUrl,method:e};return Object.assign(i,r),Object(a["a"])(i)}function v(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].EchartsListUrl+t+"/":n["a"].EchartsListUrl,method:e};return Object.assign(i,r),Object(a["a"])(i)}function _(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].ProductClassesPlanUrl+t+"/":n["a"].ProductClassesPlanUrl,method:e};return Object.assign(i,r),Object(a["a"])(i)}function R(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].ProductClassesPlanPanycreateUrl+t+"/":n["a"].ProductClassesPlanPanycreateUrl,method:e};return Object.assign(i,r),Object(a["a"])(i)}function y(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].ProductDayPlanNotice+t+"/":n["a"].ProductDayPlanNotice,method:e};return Object.assign(i,r),Object(a["a"])(i)}function M(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].HomePageUrl+t+"/":n["a"].HomePageUrl,method:e};return Object.assign(i,r),Object(a["a"])(i)}function O(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].TestIndicators+t+"/":n["a"].TestIndicators,method:e};return Object.assign(i,r),Object(a["a"])(i)}function j(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].TestSubTypes+t+"/":n["a"].TestSubTypes,method:e};return Object.assign(i,r),Object(a["a"])(i)}function x(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].MaterialTestOrders+t+"/":n["a"].MaterialTestOrders,method:e};return Object.assign(i,r),Object(a["a"])(i)}function S(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].MatIndicatorTab+t+"/":n["a"].MatIndicatorTab,method:e};return Object.assign(i,r),Object(a["a"])(i)}function w(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].MaterialDataPoints+t+"/":n["a"].MaterialDataPoints,method:e};return Object.assign(i,r),Object(a["a"])(i)}function C(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].DataPoints+t+"/":n["a"].DataPoints,method:e};return Object.assign(i,r),Object(a["a"])(i)}function N(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].TestTypes+t+"/":n["a"].TestTypes,method:e};return Object.assign(i,r),Object(a["a"])(i)}function P(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].BatchingMaterials+t+"/":n["a"].BatchingMaterials,method:e};return Object.assign(i,r),Object(a["a"])(i)}function E(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].MatTestMethods+t+"/":n["a"].MatTestMethods,method:e};return Object.assign(i,r),Object(a["a"])(i)}function k(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].MatDataPointIndicators+t+"/":n["a"].MatDataPointIndicators,method:e};return Object.assign(i,r),Object(a["a"])(i)}function I(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].MatTestIndicatorMethods+t+"/":n["a"].MatTestIndicatorMethods,method:e};return Object.assign(i,r),Object(a["a"])(i)}function T(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].LevelResult+t+"/":n["a"].LevelResult,method:e};return Object.assign(i,r),Object(a["a"])(i)}function F(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].ClassesBanburySummary+t+"/":n["a"].ClassesBanburySummary,method:e};return Object.assign(i,r),Object(a["a"])(i)}function U(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].CollectTrainsFeed+t+"/":n["a"].CollectTrainsFeed,method:e};return Object.assign(i,r),Object(a["a"])(i)}function A(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].EquipBanburySummary+t+"/":n["a"].EquipBanburySummary,method:e};return Object.assign(i,r),Object(a["a"])(i)}function L(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].CutTimeCollect+t+"/":n["a"].CutTimeCollect,method:e};return Object.assign(i,r),Object(a["a"])(i)}function $(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].SumSollectTrains+t+"/":n["a"].SumSollectTrains,method:e};return Object.assign(i,r),Object(a["a"])(i)}function B(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].PutPlanManagement+t+"/":n["a"].PutPlanManagement,method:e};return Object.assign(i,r),Object(a["a"])(i)}function V(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].MaterialCount+t+"/":n["a"].MaterialCount,method:e};return Object.assign(i,r),Object(a["a"])(i)}function D(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].InventoryLog+t+"/":n["a"].InventoryLog,method:e};return Object.assign(i,r),Object(a["a"])(i)}function W(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].PalletTrainsFeedbacks+t+"/":n["a"].PalletTrainsFeedbacks,method:e};return Object.assign(i,r),Object(a["a"])(i)}function G(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].LbPlanManagement+t+"/":n["a"].LbPlanManagement,method:e};return Object.assign(i,r),Object(a["a"])(i)}function q(e,t){var r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},i={url:t?n["a"].LabelPrint+t+"/":n["a"].LabelPrint,method:e};return Object.assign(i,r),Object(a["a"])(i)}},"2ca0":function(e,t,r){"use strict";var a=r("23e7"),n=r("06cf").f,i=r("50c4"),l=r("5a34"),o=r("1d80"),c=r("ab13"),s=r("c430"),u="".startsWith,d=Math.min,h=c("startsWith"),p=!s&&!h&&!!function(){var e=n(String.prototype,"startsWith");return e&&!e.writable}();a({target:"String",proto:!0,forced:!p&&!h},{startsWith:function(e){var t=String(o(this));l(e);var r=i(d(arguments.length>1?arguments[1]:void 0,t.length)),a=String(e);return u?u.call(t,a,r):t.slice(r,r+a.length)===a}})},6547:function(e,t,r){var a=r("a691"),n=r("1d80"),i=function(e){return function(t,r){var i,l,o=String(n(t)),c=a(r),s=o.length;return c<0||c>=s?e?"":void 0:(i=o.charCodeAt(c),i<55296||i>56319||c+1===s||(l=o.charCodeAt(c+1))<56320||l>57343?e?o.charAt(c):i:e?o.slice(c,c+2):l-56320+(i-55296<<10)+65536)}};e.exports={codeAt:i(!1),charAt:i(!0)}},7156:function(e,t,r){var a=r("861d"),n=r("d2bb");e.exports=function(e,t,r){var i,l;return n&&"function"==typeof(i=t.constructor)&&i!==r&&a(l=i.prototype)&&l!==r.prototype&&n(e,l),e}},"8aa5":function(e,t,r){"use strict";var a=r("6547").charAt;e.exports=function(e,t,r){return t+(r?a(e,t).length:1)}},9263:function(e,t,r){"use strict";var a=r("ad6d"),n=r("9f7f"),i=RegExp.prototype.exec,l=String.prototype.replace,o=i,c=function(){var e=/a/,t=/b*/g;return i.call(e,"a"),i.call(t,"a"),0!==e.lastIndex||0!==t.lastIndex}(),s=n.UNSUPPORTED_Y||n.BROKEN_CARET,u=void 0!==/()??/.exec("")[1],d=c||u||s;d&&(o=function(e){var t,r,n,o,d=this,h=s&&d.sticky,p=a.call(d),b=d.source,f=0,g=e;return h&&(p=p.replace("y",""),-1===p.indexOf("g")&&(p+="g"),g=String(e).slice(d.lastIndex),d.lastIndex>0&&(!d.multiline||d.multiline&&"\n"!==e[d.lastIndex-1])&&(b="(?: "+b+")",g=" "+g,f++),r=new RegExp("^(?:"+b+")",p)),u&&(r=new RegExp("^"+b+"$(?!\\s)",p)),c&&(t=d.lastIndex),n=i.call(h?r:d,g),h?n?(n.input=n.input.slice(f),n[0]=n[0].slice(f),n.index=d.lastIndex,d.lastIndex+=n[0].length):d.lastIndex=0:c&&n&&(d.lastIndex=d.global?n.index+n[0].length:t),u&&n&&n.length>1&&l.call(n[0],r,(function(){for(o=1;o<arguments.length-2;o++)void 0===arguments[o]&&(n[o]=void 0)})),n}),e.exports=o},"9f7f":function(e,t,r){"use strict";var a=r("d039");function n(e,t){return RegExp(e,t)}t.UNSUPPORTED_Y=a((function(){var e=n("a","y");return e.lastIndex=2,null!=e.exec("abcd")})),t.BROKEN_CARET=a((function(){var e=n("^r","gy");return e.lastIndex=2,null!=e.exec("str")}))},a434:function(e,t,r){"use strict";var a=r("23e7"),n=r("23cb"),i=r("a691"),l=r("50c4"),o=r("7b0b"),c=r("65f0"),s=r("8418"),u=r("1dde"),d=r("ae40"),h=u("splice"),p=d("splice",{ACCESSORS:!0,0:0,1:2}),b=Math.max,f=Math.min,g=9007199254740991,m="Maximum allowed length exceeded";a({target:"Array",proto:!0,forced:!h||!p},{splice:function(e,t){var r,a,u,d,h,p,v=o(this),_=l(v.length),R=n(e,_),y=arguments.length;if(0===y?r=a=0:1===y?(r=0,a=_-R):(r=y-2,a=f(b(i(t),0),_-R)),_+r-a>g)throw TypeError(m);for(u=c(v,a),d=0;d<a;d++)h=R+d,h in v&&s(u,d,v[h]);if(u.length=a,r<a){for(d=R;d<_-a;d++)h=d+a,p=d+r,h in v?v[p]=v[h]:delete v[p];for(d=_;d>_-a+r;d--)delete v[d-1]}else if(r>a)for(d=_-a;d>R;d--)h=d+a-1,p=d+r-1,h in v?v[p]=v[h]:delete v[p];for(d=0;d<r;d++)v[d+R]=arguments[d+2];return v.length=_-a+r,u}})},a9e3:function(e,t,r){"use strict";var a=r("83ab"),n=r("da84"),i=r("94ca"),l=r("6eeb"),o=r("5135"),c=r("c6b6"),s=r("7156"),u=r("c04e"),d=r("d039"),h=r("7c73"),p=r("241c").f,b=r("06cf").f,f=r("9bf2").f,g=r("58a8").trim,m="Number",v=n[m],_=v.prototype,R=c(h(_))==m,y=function(e){var t,r,a,n,i,l,o,c,s=u(e,!1);if("string"==typeof s&&s.length>2)if(s=g(s),t=s.charCodeAt(0),43===t||45===t){if(r=s.charCodeAt(2),88===r||120===r)return NaN}else if(48===t){switch(s.charCodeAt(1)){case 66:case 98:a=2,n=49;break;case 79:case 111:a=8,n=55;break;default:return+s}for(i=s.slice(2),l=i.length,o=0;o<l;o++)if(c=i.charCodeAt(o),c<48||c>n)return NaN;return parseInt(i,a)}return+s};if(i(m,!v(" 0o1")||!v("0b1")||v("+0x1"))){for(var M,O=function(e){var t=arguments.length<1?0:e,r=this;return r instanceof O&&(R?d((function(){_.valueOf.call(r)})):c(r)!=m)?s(new v(y(t)),r,O):y(t)},j=a?p(v):"MAX_VALUE,MIN_VALUE,NaN,NEGATIVE_INFINITY,POSITIVE_INFINITY,EPSILON,isFinite,isInteger,isNaN,isSafeInteger,MAX_SAFE_INTEGER,MIN_SAFE_INTEGER,parseFloat,parseInt,isInteger".split(","),x=0;j.length>x;x++)o(v,M=j[x])&&!o(O,M)&&f(O,M,b(v,M));O.prototype=_,_.constructor=O,l(n,m,O)}},ac1f:function(e,t,r){"use strict";var a=r("23e7"),n=r("9263");a({target:"RegExp",proto:!0,forced:/./.exec!==n},{exec:n})},b289:function(e,t,r){},cf45:function(e,t,r){"use strict";t["a"]={formLabelWidth:"120px",statusList:[{id:1,name:"完成"},{id:2,name:"执行中"},{id:3,name:"失败"},{id:4,name:"新建"},{id:5,name:"关闭"}]}},d784:function(e,t,r){"use strict";r("ac1f");var a=r("6eeb"),n=r("d039"),i=r("b622"),l=r("9263"),o=r("9112"),c=i("species"),s=!n((function(){var e=/./;return e.exec=function(){var e=[];return e.groups={a:"7"},e},"7"!=="".replace(e,"$<a>")})),u=function(){return"$0"==="a".replace(/./,"$0")}(),d=i("replace"),h=function(){return!!/./[d]&&""===/./[d]("a","$0")}(),p=!n((function(){var e=/(?:)/,t=e.exec;e.exec=function(){return t.apply(this,arguments)};var r="ab".split(e);return 2!==r.length||"a"!==r[0]||"b"!==r[1]}));e.exports=function(e,t,r,d){var b=i(e),f=!n((function(){var t={};return t[b]=function(){return 7},7!=""[e](t)})),g=f&&!n((function(){var t=!1,r=/a/;return"split"===e&&(r={},r.constructor={},r.constructor[c]=function(){return r},r.flags="",r[b]=/./[b]),r.exec=function(){return t=!0,null},r[b](""),!t}));if(!f||!g||"replace"===e&&(!s||!u||h)||"split"===e&&!p){var m=/./[b],v=r(b,""[e],(function(e,t,r,a,n){return t.exec===l?f&&!n?{done:!0,value:m.call(t,r,a)}:{done:!0,value:e.call(r,t,a)}:{done:!1}}),{REPLACE_KEEPS_$0:u,REGEXP_REPLACE_SUBSTITUTES_UNDEFINED_CAPTURE:h}),_=v[0],R=v[1];a(String.prototype,e,_),a(RegExp.prototype,b,2==t?function(e,t){return R.call(e,this,t)}:function(e){return R.call(e,this)})}d&&o(RegExp.prototype[b],"sham",!0)}},d9259:function(e,t,r){"use strict";var a=r("b289"),n=r.n(a);n.a},f41e:function(e,t,r){"use strict";r.r(t);var a=function(){var e=this,t=e.$createElement,r=e._self._c||t;return r("div",[r("el-form",{attrs:{inline:!0}},[r("el-form-item",{staticStyle:{float:"left"},attrs:{label:"胶料编码"}},[r("el-input",{on:{input:e.productNoChange},model:{value:e.productNo,callback:function(t){e.productNo=t},expression:"productNo"}})],1),r("el-form-item",{staticStyle:{float:"left"},attrs:{label:"胶料名称"}},[r("el-input",{on:{input:e.productNameChange},model:{value:e.productName,callback:function(t){e.productName=t},expression:"productName"}})],1),e.permissionObj.productinfo.indexOf("add")>-1?r("el-form-item",{staticStyle:{float:"right"}},[r("el-button",{on:{click:e.showAddRubberRecipeDialog}},[e._v("新建")])],1):e._e()],1),r("el-table",{staticStyle:{width:"100%"},attrs:{"highlight-current-row":"",data:e.tableData,border:""},on:{"row-click":e.handleCurrentChange}},[r("el-table-column",{attrs:{type:"index",width:"50",label:"No"}}),r("el-table-column",{attrs:{prop:"product_no",label:"胶料编码"}}),r("el-table-column",{attrs:{prop:"product_name",label:"胶料名称"}}),r("el-table-column",{attrs:{prop:"created_username",label:"创建用户"}}),r("el-table-column",{attrs:{prop:"created_date",label:"创建日期"}})],1),r("pagination",{attrs:{total:e.total,"current-page":e.getParams.page},on:{currentChange:e.currentChange}}),r("el-dialog",{attrs:{"close-on-click-modal":!1,"close-on-press-escape":!1,title:"新建胶料代码",visible:e.dialogAddRubberRecipe},on:{"update:visible":function(t){e.dialogAddRubberRecipe=t}}},[r("el-form",{attrs:{"label-width":e.formLabelWidth},model:{value:e.rubberRecipeForm,callback:function(t){e.rubberRecipeForm=t},expression:"rubberRecipeForm"}},[r("el-form-item",{attrs:{error:e.rubberRecipeFormError.product_no,label:"胶料编码","label-width":e.formLabelWidth}},[r("el-input",{model:{value:e.rubberRecipeForm.product_no,callback:function(t){e.$set(e.rubberRecipeForm,"product_no",t)},expression:"rubberRecipeForm.product_no"}})],1),r("el-form-item",{attrs:{error:e.rubberRecipeFormError.product_name,label:"胶料名称","label-width":e.formLabelWidth}},[r("el-input",{model:{value:e.rubberRecipeForm.product_name,callback:function(t){e.$set(e.rubberRecipeForm,"product_name",t)},expression:"rubberRecipeForm.product_name"}})],1),r("el-form-item",[r("p",{staticStyle:{color:"red"}},[e._v(e._s(e.rubberRecipeError))])])],1),r("div",{staticClass:"dialog-footer",attrs:{slot:"footer"},slot:"footer"},[r("el-button",{on:{click:function(t){e.dialogAddRubberRecipe=!1}}},[e._v("取 消")]),r("el-button",{attrs:{type:"primary"},on:{click:e.handleAddRubberRecipe}},[e._v("生成")])],1)],1),r("el-dialog",{attrs:{"close-on-click-modal":!1,"close-on-press-escape":!1,width:"80%",title:"选择原材料",visible:e.dialogChoiceMaterials},on:{"update:visible":function(t){e.dialogChoiceMaterials=t},open:e.dialogChoiceMaterialsOpen}},[r("el-row",[r("el-form",{attrs:{inline:!0}},[r("el-form-item",{staticStyle:{float:"right"}},[r("el-button",{on:{click:e.rmClicked}},[e._v("RM")])],1),r("el-form-item",{staticStyle:{float:"right"}},[r("el-button",{on:{click:e.selectClicked}},[e._v("选择")])],1)],1)],1),r("el-row",{attrs:{gutter:15}},[r("el-col",{attrs:{span:12}},[r("el-table",{ref:"allMaterialsMultipleTable",staticStyle:{width:"100%"},attrs:{height:"250",border:"",data:e.materials},on:{"selection-change":e.handleMaterialsSelectionChange}},[r("el-table-column",{attrs:{type:"selection",width:"55"}}),r("el-table-column",{attrs:{label:"原材料代码",prop:"material_no"}}),r("el-table-column",{attrs:{label:"原材料名称",prop:"material_name"}})],1)],1),r("el-col",{attrs:{span:12}},[r("el-table",{ref:"materialsMultipleTable",staticStyle:{width:"100%"},attrs:{border:"",data:e.selectedMaterials},on:{select:e.handleSelect,"selection-change":e.handleSelectedMaterialsSelectionChange}},[r("el-table-column",{attrs:{type:"selection",width:"55"}}),r("el-table-column",{attrs:{label:"原材料代码",prop:"material_no"}}),r("el-table-column",{attrs:{label:"原材料名称",prop:"material_name"}}),r("el-table-column",{attrs:{label:"车次"},scopedSlots:e._u([{key:"default",fn:function(t){return[t.row.id?r("el-select",{attrs:{placeholder:"请选择"},model:{value:t.row.car_number,callback:function(r){e.$set(t.row,"car_number",r)},expression:"scope.row.car_number"}},e._l(e.carNumberOptionsNotRm,(function(e){return r("el-option",{key:e.id,attrs:{label:e.global_name,value:e.global_name}})})),1):r("el-select",{attrs:{placeholder:"请选择"},model:{value:t.row.car_number,callback:function(r){e.$set(t.row,"car_number",r)},expression:"scope.row.car_number"}},e._l(e.carNumberOptionsRm,(function(e){return r("el-option",{key:e.id,attrs:{label:e.global_name,value:e.global_name}})})),1)]}}])})],1)],1)],1)],1),r("el-dialog",{attrs:{"close-on-click-modal":!1,"close-on-press-escape":!1,title:"胶料配方标准",visible:e.dialogRubberRecipeStandard},on:{"update:visible":function(t){e.dialogRubberRecipeStandard=t}}},[r("el-form",{attrs:{inline:!0}},[r("el-form-item",{staticStyle:{float:"right"}},[1===e.currentRow.used_type||-1===e.currentRow.used_type?r("el-button",{on:{click:e.newClicked}},[e._v("新建 ")]):e._e()],1),r("el-form-item",{staticStyle:{float:"right"}},[1===e.currentRow.used_type||-1===e.currentRow.used_type?r("el-button",{on:{click:e.saveClicked}},[e._v("保存 ")]):e._e()],1)],1),r("table",{staticClass:"table table-bordered",staticStyle:{width:"100%",color:"#909399","font-size":"14px"}},[r("thead",[r("tr",[r("th",[e._v("S")]),r("th",[e._v("No")]),r("th",[e._v("段次")]),r("th",[e._v("类别")]),r("th",[e._v("原材料")]),r("th",[e._v("配比")]),r("th",[e._v("配比累计")])])]),r("tbody",{staticStyle:{color:"#606266"}},[r("tr",{staticStyle:{background:"rgba(189,198,210,0.73)"}},[r("td",{staticStyle:{"text-align":"center"},attrs:{colspan:"5"}},[e._v("配方结果")]),r("td",{staticStyle:{"text-align":"center"}},[e._v(e._s(e.ratioSum))]),r("td")]),e._l(e.selectedMaterials,(function(t,a){return r("tr",{key:a},[r("td"),r("td",[e._v(e._s(a+1))]),r("td",[e._v(e._s(t.car_number))]),r("td",[e._v(e._s(t.material_type_name))]),r("td",[e._v(e._s(t.material_name))]),r("td",{staticStyle:{"text-align":"center"}},[t.car_number&&0!==t.car_number.indexOf("RM")?r("el-input-number",{attrs:{disabled:-1!==e.currentRow.used_type&&1!==e.currentRow.used_type,precision:2,step:.1},on:{change:e.carNumberChanged},model:{value:t.ratio,callback:function(r){e.$set(t,"ratio",e._n(r))},expression:"material.ratio"}}):e._e()],1),r("td",[e._v(e._s(t.ratio_sum))])])}))],2)])],1),r("el-dialog",{attrs:{title:"复制生成新的胶料标准","close-on-click-modal":!1,"close-on-press-escape":!1,visible:e.dialogCopyRubberRecipeStandardVisible},on:{"update:visible":function(t){e.dialogCopyRubberRecipeStandardVisible=t}}},[r("el-form",{attrs:{"label-width":e.formLabelWidth}},[r("el-form-item",{attrs:{label:"来源胶料"}},[r("el-col",{attrs:{span:6}},[r("el-input",{attrs:{disabled:""},model:{value:e.sourceFactory,callback:function(t){e.sourceFactory=t},expression:"sourceFactory"}})],1),r("el-col",{staticClass:"line",attrs:{span:2}},[e._v("-")]),r("el-col",{attrs:{span:6}},[r("el-input",{attrs:{disabled:""},model:{value:e.sourceProductNo,callback:function(t){e.sourceProductNo=t},expression:"sourceProductNo"}})],1),r("el-col",{staticClass:"line",attrs:{span:2}},[e._v("-")]),r("el-col",{attrs:{span:6}},[r("el-input",{attrs:{disabled:""},model:{value:e.sourceVersion,callback:function(t){e.sourceVersion=t},expression:"sourceVersion"}})],1)],1),r("el-form-item",{attrs:{label:"新建胶料"}},[r("el-col",{attrs:{span:6}},[r("el-select",{attrs:{placeholder:"请选择"},model:{value:e.newFactory,callback:function(t){e.newFactory=t},expression:"newFactory"}},e._l(e.originOptions,(function(e){return r("el-option",{key:e.id,attrs:{label:e.global_name,value:e.id}})})),1)],1),r("el-col",{staticClass:"line",attrs:{span:2}},[e._v("-")]),r("el-col",{attrs:{span:6}},[r("el-input",{model:{value:e.newProductNo,callback:function(t){e.newProductNo=t},expression:"newProductNo"}})],1),r("el-col",{staticClass:"line",attrs:{span:2}},[e._v("-")]),r("el-col",{attrs:{span:6}},[r("el-input",{model:{value:e.newVersion,callback:function(t){e.newVersion=t},expression:"newVersion"}})],1)],1),r("el-form-item",[r("p",{staticStyle:{color:"red"}},[e._v(e._s(e.copyError))])])],1),r("div",{staticClass:"dialog-footer",attrs:{slot:"footer"},slot:"footer"},[r("el-button",{attrs:{type:"primary"},on:{click:e.handleCopyRubberRecipeStandard}},[e._v("复制")])],1)],1)],1)},n=[],i=(r("4160"),r("c975"),r("a15b"),r("a434"),r("a9e3"),r("b680"),r("ac1f"),r("1276"),r("2ca0"),r("159b"),r("5530")),l=r("3e51"),o=r("1f6c"),c=r("cf45"),s=r("2f62"),u={components:{pagination:l["a"]},data:function(){return{tableData:[],getParams:{page:1},formLabelWidth:c["a"].formLabelWidth,dialogAddRubberRecipe:!1,originOptions:[],rubberRecipeForm:{product_no:"",product_name:""},rubberRecipeFormError:{product_no:"",product_name:""},materials:[],selectedMaterials:[],dialogChoiceMaterials:!1,dialogRubberRecipeStandard:!1,selectingMaterial:!1,toggleMaterials:!1,carNumberOptionsNotRm:[],carNumberOptionsRm:[],ratioSum:0,rubberRecipeError:"",carNumberIdByName:{},currentRow:{used_type:-1},materialById:{},dialogCopyRubberRecipeStandardVisible:!1,sourceFactory:"",sourceProductNo:"",sourceVersion:"",newFactory:"",newProductNo:"",newVersion:"",originByName:{},copyError:"",productNo:"",productName:"",currentPage:1,total:0}},computed:Object(i["a"])({},Object(s["b"])(["permission"])),created:function(){this.permissionObj=this.permission;var e=this;this.getList(),Object(o["k"])("get",{params:{class_name:"产地"}}).then((function(t){e.originOptions=t.results;for(var r=0;r<e.originOptions.length;++r)e.originByName[e.originOptions[r].global_name]=e.originOptions[r]})).catch((function(){})),Object(o["y"])("get",null,{params:{all:1}}).then((function(t){e.materials=t.results;for(var r=0;r<e.materials.length;++r)e.materialById[e.materials[r].id]=e.materials[r]})).catch((function(){})),Object(o["k"])("get",{params:{class_name:"胶料段次"}}).then((function(t){for(var r=0;r<t.results.length;++r)e.carNumberIdByName[t.results[r].global_name]=t.results[r].id,t.results[r].global_name.startsWith("RM")?e.carNumberOptionsRm.push(t.results[r]):e.carNumberOptionsNotRm.push(t.results[r])})).catch((function(){}))},methods:{getList:function(){var e=this;Object(o["G"])("get",null,{params:this.getParams}).then((function(t){e.total=t.count,e.tableData=t.results})).catch((function(){}))},currentChange:function(e){this.getParams.page=e,this.getList()},productNoChange:function(){this.getParams["product_no"]=this.productNo,this.getParams.page=1,this.getList()},productNameChange:function(){this.getParams["product_name"]=this.productName,this.getParams.page=1,this.getList()},usedTypeFormatter:function(e,t){return this.usedTypeChoice(e.used_type)},usedTypeChoice:function(e){switch(e){case 1:return"编辑";case 2:return"通过";case 3:return"应用";case 4:return"驳回";case 5:return"废弃"}},updateFlag:function(e,t){var r=this;Object(o["G"])("patch",e,{data:t}).then((function(e){r.currentChange(r.currentPage)}))},pass:function(e){this.updateFlag(e.id,!0)},reject:function(e){this.updateFlag(e.id,!1)},apply:function(e){this.updateFlag(e.id,!0)},discard:function(e){this.updateFlag(e.id,!1)},showAddRubberRecipeDialog:function(){this.rubberRecipeError="",this.rubberRecipeForm={product_no:"",product_name:""},this.dialogAddRubberRecipe=!0,this.currentRow={used_type:-1}},handleAddRubberRecipe:function(){this.rubberRecipeFormError={product_no:"",product_name:""};var e=this;Object(o["G"])("post",null,{data:{product_no:e.rubberRecipeForm.product_no,product_name:e.rubberRecipeForm.product_name}}).then((function(t){e.$message.success(e.rubberRecipeForm.product_name+"创建成功"),e.getParams.page=1,e.getList(),e.dialogAddRubberRecipe=!1})).catch((function(t){e.rubberRecipeFormError.product_no=t.product_no.join(","),e.rubberRecipeFormError.product_name=t.product_name.join(",")}))},handleMaterialsSelectionChange:function(e){if(!this.toggleMaterials){this.selectingMaterial=!0;for(var t=0;t<e.length;++t)-1===this.selectedMaterials.indexOf(e[t])&&this.selectedMaterials.push(e[t]);for(var r=0;r<this.selectedMaterials.length;++r)this.selectedMaterials[r].id&&-1===e.indexOf(this.selectedMaterials[r])&&(this.selectedMaterials.splice(r,1),--r);var a=this;setTimeout((function(){e&&e.forEach((function(e){a.$refs.materialsMultipleTable.toggleRowSelection(e,!0)})),a.selectingMaterial=!1}),0)}},handleSelectedMaterialsSelectionChange:function(e){if(!this.selectingMaterial&&!this.toggleMaterials){for(var t=0;t<this.materials.length;++t){var r=this.materials[t];-1===e.indexOf(r)&&this.$refs.allMaterialsMultipleTable.toggleRowSelection(r,!1)}if(!e.length)for(var a=0;a<this.selectedMaterials.length;++a)this.selectedMaterials[a].id||(this.selectedMaterials.splice(a,1),--a)}},rmClicked:function(){var e={};this.selectedMaterials.push(e);var t=this;t.$refs.materialsMultipleTable.toggleRowSelection(t.selectedMaterials[t.selectedMaterials.length-1],!0)},handleSelect:function(e,t){t.id||this.selectedMaterials.splice(this.selectedMaterials.indexOf(t),1)},initRatio:function(){for(var e=0;e<this.selectedMaterials.length;++e)0===this.selectedMaterials[e].car_number.indexOf("RM")||this.selectedMaterials[e].ratio||this.$set(this.selectedMaterials[e],"ratio",0),this.selectedMaterials[e].ratio_sum||this.$set(this.selectedMaterials[e],"ratio_sum",0)},selectClicked:function(){if(this.selectedMaterials.length){for(var e=0;e<this.selectedMaterials.length;++e)if(!this.selectedMaterials[e].car_number)return void this.$alert("请选择所有原材料车次","警告",{confirmButtonText:"确定"});this.initRatio(),this.carNumberChanged(),this.dialogChoiceMaterials=!1,this.dialogRubberRecipeStandard=!0}},newClicked:function(){this.dialogRubberRecipeStandard=!1,this.dialogChoiceMaterials=!0},saveClicked:function(){for(var e=0,t=0;t<this.selectedMaterials.length;++t)!this.selectedMaterials[t].material_type_name||"天然胶"!==this.selectedMaterials[t].material_type_name&&"合成胶"!==this.selectedMaterials[t].material_type_name||(e+=this.selectedMaterials[t].ratio);if(100!==e)this.$alert("天然胶加合成胶总配比必须为100","警告",{confirmButtonText:"确定"});else{var r=this,a=[];for(t=0;t<this.selectedMaterials.length;++t){var n={stage:r.carNumberIdByName[r.selectedMaterials[t].car_number],sn:t,ratio:r.selectedMaterials[t].ratio};this.selectedMaterials[t].id&&(n.material=this.selectedMaterials[t].id),a.push(n)}-1!==this.currentRow.used_type?Object(o["G"])("put",this.currentRow.id,{data:{productrecipe_set:a}}).then((function(e){r.dialogRubberRecipeStandard=!1,r.$message(r.currentRow.product_name+"修改成功"),r.currentChange(r.currentPage)})).catch((function(){})):Object(o["G"])("post",null,{data:{product_no:r.rubberRecipeForm.product_no,product_name:r.rubberRecipeForm.product_name,productrecipe_set:a}}).then((function(e){r.dialogRubberRecipeStandard=!1,r.$message(r.rubberRecipeForm.product_name+"创建成功"),r.currentChange(r.currentPage)})).catch((function(){}))}},afterGetData:function(){this.currentRow={used_type:-1}},carNumberChanged:function(){for(var e=0;e<this.selectedMaterials.length;++e)this.selectedMaterials[e-1]?this.selectedMaterials[e].ratio?this.selectedMaterials[e].ratio_sum=this.selectedMaterials[e].ratio+this.selectedMaterials[e-1].ratio_sum:this.selectedMaterials[e].ratio_sum=this.selectedMaterials[e-1].ratio_sum:this.selectedMaterials[e].ratio_sum=this.selectedMaterials[e].ratio,this.selectedMaterials[e].ratio_sum=Number(this.selectedMaterials[e].ratio_sum.toFixed(2));this.ratioSum=this.selectedMaterials[this.selectedMaterials.length-1].ratio_sum},handleCurrentChange:function(e){this.currentRow=e},showRubberRecipeStandardDialog:function(){var e=this;Object(o["G"])("get",this.currentRow.id).then((function(t){e.selectedMaterials=[];for(var r=0;r<t.productrecipe_set.length;++r)if(t.productrecipe_set[r].material){var a=e.materialById[t.productrecipe_set[r].material];a.car_number=t.productrecipe_set[r].stage_name,a.ratio=Number(t.productrecipe_set[r].ratio),e.selectedMaterials.push(a)}else e.selectedMaterials.push({car_number:t.productrecipe_set[r].stage_name});e.selectedMaterials.length&&(e.initRatio(),e.carNumberChanged(),e.dialogRubberRecipeStandard=!0)})).catch((function(){}))},dialogChoiceMaterialsOpen:function(){if(this.selectedMaterials.length){var e=this;this.toggleMaterials=!0,setTimeout((function(){for(var t=0;t<e.selectedMaterials.length;++t){e.$refs.materialsMultipleTable.toggleRowSelection(e.selectedMaterials[t],!0);for(var r=0;r<e.materials.length;++r)if(e.selectedMaterials[t].id&&e.materials[r].id===e.selectedMaterials[t].id){e.$refs.allMaterialsMultipleTable.toggleRowSelection(e.materials[r],!0);break}}e.toggleMaterials=!1}),0)}},copyRecipeClicked:function(){var e=this.currentRow.product_standard_no.split("-");this.sourceFactory=this.currentRow.factory,this.sourceProductNo=e[1],this.sourceVersion=e[2],this.newFactory=this.originByName[this.sourceFactory].id,this.newProductNo=this.sourceProductNo;var t=Number(this.sourceVersion);isNaN(t)?this.newVersion=this.sourceVersion:this.newVersion=t+1,this.dialogCopyRubberRecipeStandardVisible=!0},handleCopyRubberRecipeStandard:function(){this.copyError="";var e=this;Object(o["e"])("post",{data:{product_info_id:e.currentRow.id,factory:e.newFactory,versions:e.newVersion}}).then((function(t){e.dialogCopyRubberRecipeStandardVisible=!1,e.$message(e.currentRow.product_standard_no+"拷贝成功"),e.currentChange(e.currentPage)})).catch((function(t){e.copyError=t.non_field_errors[0]}))}}},d=u,h=(r("d9259"),r("2877")),p=Object(h["a"])(d,a,n,!1,null,"3fde6c36",null);t["default"]=p.exports}}]);