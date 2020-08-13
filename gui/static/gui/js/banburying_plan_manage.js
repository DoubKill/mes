;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {

            return {
                tableData: [],
            }
        },

        created: function () {

            var app = this;
            axios.get(BanburyPlanUrl, {
            }).then(function (response) {
                app.tableData = response.data.data;
            }).catch(function (error) {
            });


        },


        methods: {
            SearchBanburyPlan: function(){

            },
            currentChange() {
            },
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();