;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {

            return {
                tableDataUrl: ProductDayPlansUrl,
                plan_date: dayjs().format("YYYY-MM-DD"),
                equips: [],
                equip_no: "",
                stage_product_batch_no: "",
                stage_product_batch_nos: [],
                addRubberDailyPlanDialogVisible: false,
                rubberDailyPlanForm: {
                    equip: null,
                    product_batching: null,
                    pdp_product_classes_plan: [
                        {
                            sn: null,
                            plan_trains: null,
                            time: "00:00:00",
                            weight: "",
                            unit: ""
                        }, {
                            sn: null,
                            plan_trains: null,
                            time: "00:00:00",
                            weight: "",
                            unit: ""
                        }, {
                            sn: null,
                            plan_trains: null,
                            time: "00:00:00",
                            weight: "",
                            unit: ""
                        }
                    ]
                },
                productBatchings: []
            }
        },
        created: function () {

            var app = this;
            axios.get(EquipUrl, {
                params: {
                    page_size: 100000000
                }
            }).then(function (response) {

                app.equips = response.data.results;
            }).catch(function (error) {

            });
            axios.get(RubberMaterialUrl, {

                params: {
                    page_size: 100000000
                }
            }).then(function (response) {

                app.stage_product_batch_nos = [];
                app.productBatchings = response.data.results;
                response.data.results.forEach(function (batching) {

                    if (app.stage_product_batch_nos.indexOf(batching.stage_product_batch_no) === -1) {

                        app.stage_product_batch_nos.push(batching.stage_product_batch_no)
                    }
                });
            }).catch(function (error) {

            });
        },
        methods: {

            queryDataChange: function () {

                this.currentChange(this.currentRow);
            },
            beforeGetData: function () {

                this.getParams["plan_date"] = this.plan_date;
                this.getParams["equip_no"] = this.equip_no;
                this.getParams["product_no"] = this.stage_product_batch_no
            },
            addPlanClicked: function () {

                this.addRubberDailyPlanDialogVisible = true
            },
            getPlanText: function (index) {

                switch (index) {

                    case 0:
                        return "早班计划";
                    case 1:
                        return "中班计划";
                    case 2:
                        return "晚班计划"
                }
            },
            addRubberDailyPlan: function () {

                var app = this;
                this.rubberDailyPlanForm["plan_date"] = this.plan_date;
                axios.post(ProductDayPlansUrl, this.rubberDailyPlanForm)
                    .then(function (response) {

                        app.currentChange(app.currentRow);
                    }).catch(function (error) {

                        console.log(error.data)
                });
                console.log(this.rubberDailyPlanForm)
            }
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();