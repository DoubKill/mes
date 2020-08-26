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
            afterGetData: function () {
                console.log(this.tableData)
            },
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();