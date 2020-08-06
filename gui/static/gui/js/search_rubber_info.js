;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {

            return {
                all:'',
                tableDataUrl: RubberMaterialUrl,
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

            formatter: function (row, column) {

                return row.used_type===1 ?
                    "编辑" : row.used_type===2 ?
                        "通过" : row.used_type===3 ?
                            "应用" : row.used_type===4 ?
                                "驳回" : row.used_type===5 ?
                                    "废弃" : "NULL"
            },
            beforeGetData() {

                this.getParams["stage_id"] = this.stage;
                this.getParams["dev_type"] = this.equipCatagory;
                this.getParams["factory_id"] = this.factory;
            },
            stageChange: function () {

                this.getFirstPage();
            },
            equipCatagoryChange: function () {

                this.getFirstPage();
            },
            factoryChange: function () {

                this.getFirstPage();
            },

        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();