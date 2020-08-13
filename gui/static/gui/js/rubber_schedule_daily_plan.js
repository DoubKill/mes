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
                rubberDailyPlanForm: {
                    equip: null,
                    product_batching: null,
                    pdp_product_classes_plan: [
                        {
                            sn: null,
                            plan_trains: null,
                            time: "00:00:00",
                            weight: "",
                            unit: "吨"
                        }, {
                            sn: null,
                            plan_trains: null,
                            time: "00:00:00",
                            weight: "",
                            unit: "吨"
                        }, {
                            sn: null,
                            plan_trains: null,
                            time: "00:00:00",
                            weight: "",
                            unit: "吨"
                        }
                    ]
                },
                batching_weight: "",
                batching_time_interval: "",
                productBatchings: [],
                planSchedules: [],
                productBatchingById: {},
                addPlanVisible: false,
                currentRow: null
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

                    app.productBatchingById[batching.id] = batching;
                    if (app.stage_product_batch_nos.indexOf(batching.stage_product_batch_no) === -1) {

                        app.stage_product_batch_nos.push(batching.stage_product_batch_no)
                    }
                });
            }).catch(function (error) {

            });
            axios.get(PlanScheduleUrl, {

                params: {
                    page_size: 100000000
                }
            }).then(function (response) {

                app.planSchedules = response.data.results;
            }).catch(function (error) {

            });
        },
        methods: {

            afterGetData: function () {

                console.log(this.tableData)
            },

            queryDataChange: function () {

                this.currentChange(this.currentRow);
            },

            beforeGetData: function () {

                this.getParams["plan_date"] = this.plan_date;
                this.getParams["equip_no"] = this.equip_no;
                this.getParams["product_no"] = this.stage_product_batch_no
            },
            planTrainsChange: function (index) {

                this.rubberDailyPlanForm
                    .pdp_product_classes_plan[index].weight =
                    this.batching_weight * this.rubberDailyPlanForm
                        .pdp_product_classes_plan[index].plan_trains;
                var time = this.batching_time_interval.split(":");
                var second = Number(time[2]) + Number(time[1]) * 60 + Number(time[0]) * 60 * 60;
                second = this.rubberDailyPlanForm
                    .pdp_product_classes_plan[index].plan_trains * second;
                var date = new Date(null);
                date.setSeconds(second);
                this.rubberDailyPlanForm.pdp_product_classes_plan[index].time =
                    date.toISOString().substr(11, 8);
            },
            addPlan: function () {

                var app = this;
                this.rubberDailyPlanForm["plan_date"] = this.plan_date;
                axios.post(ProductDayPlansUrl, this.rubberDailyPlanForm)
                    .then(function (response) {

                        app.$message("创建成功");
                        app.currentChange(app.currentPage);
                    }).catch(function (error) {

                    var text = "";
                    for (var key in error.response.data) {

                        text += error.response.data[key] + "\n";
                    }
                    app.$message(text);

                });
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
            productBatchingChange: function () {

                this.batching_weight = this.productBatchingById[this.rubberDailyPlanForm.product_batching].batching_weight;
                this.batching_time_interval = this.productBatchingById[this.rubberDailyPlanForm.product_batching].batching_time_interval;


                for (var i = 0; i < 3; ++i)
                    this.planTrainsChange(i)
            },
            handleCurrentChange(val) {
                this.currentRow = val;
            },
            deletePlan: function () {

                var app = this;
                this.$confirm('此操作将永久删除' + this.currentRow.product_no + ', 是否继续?', '提示', {
                    confirmButtonText: '确定',
                    cancelButtonText: '取消',
                    type: 'warning'
                }).then(() => {

                    axios.delete(ProductDayPlansUrl + app.currentRow.id + '/')
                        .then(function (response) {
                            app.$message({
                                type: 'success',
                                message: '删除成功!'
                            });
                            app.currentChange(app.currentPage);
                        }).catch(function (error) {

                        app.$message.error(error);
                    });


                }).catch(() => {

                });
            }
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();