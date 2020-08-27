;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {
            return {
                tableDataUrl: PlanScheduleUrl
            }
        },
        created: function () {

        },
        methods: {
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();