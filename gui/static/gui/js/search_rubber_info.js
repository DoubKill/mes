;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {

            return {
                stage: '',
                equipCatagory: '',
                factory: '',
                stageOptions: [],
                equipCatagoryOptions: [],
                factoryOptions: [],

            }
        },
        created: function () {

            var app = this;
            axios.get(GlobalCodesUrl, {

                params: {

                    class_name: "段次"
                }
            }).then(function (response) {

                app.stageOptions = response.data.results;
            }).catch(function (error) {

            });
            axios.get(GlobalCodesUrl, {

                params: {

                    class_name: "炼胶机类型"
                }
            }).then(function (response) {

                app.equipCatagoryOptions = response.data.results;
            }).catch(function (error) {

            });
            axios.get(GlobalCodesUrl, {

                params: {

                    class_name: "产地"
                }
            }).then(function (response) {

                app.factoryOptions = response.data.results;
            }).catch(function (error) {

            });
        },
        methods: {


        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();