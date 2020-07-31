;(function () {

    var Main = {

        mixins: [BaseMixin],

    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount('#app')
})();