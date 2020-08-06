;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {

        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();