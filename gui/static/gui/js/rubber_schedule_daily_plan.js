;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {

            return {
                tableDataUrl: ProductDayPlansUrl,
                plan_date: dayjs().format("YYYY-MM-DD"),
                equips: [],
                equipById: {},
                equip_no: "",
                stage_product_batch_no: "",
                stage_product_batch_nos: [],
                rubberDailyPlanChangeForm: {

                    equip: null,
                    product_batching: null,
                    pdp_product_classes_plan: [
                        {
                            sn: null,
                            plan_trains: null,
                            time: "00:00:00",
                            weight: "",
                        }, {
                            sn: null,
                            plan_trains: null,
                            time: "00:00:00",
                            weight: "",
                        }, {
                            sn: null,
                            plan_trains: null,
                            time: "00:00:00",
                            weight: "",
                        }
                    ]
                },
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
                batching_weight_for_update: "",
                batching_time_interval_for_update: "",
                productBatchings: [],
                planSchedules: [],
                productBatchingById: {},
                addPlanVisible: false,
                changePlanVisible: false,
                currentRow: null,
                dialogCopyVisible: false,
                src_date: null,
                dst_date: null,
                plansForAdd: [],
                statisticData: [],
                equipIdForAdd: null
            }
        },
        created: function () {

            var app = this;
            axios.get(EquipUrl, {
                params: {
                    all: 1
                    // page_size: 100000000
                }
            }).then(function (response) {

                app.equips = response.data.results;
                app.equips.forEach(function (equip) {

                    app.equipById[equip.id] = equip;
                })
            }).catch(function (error) {

            });
            axios.get(RubberMaterialUrl, {

                params: {
                    all: 1
                    // page_size: 100000000
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
                    // page_size: 100000000
                    all: 1
                }
            }).then(function (response) {

                app.planSchedules = response.data.results;
            }).catch(function (error) {

            });
        },
        methods: {

            queryDataChange: function () {

                this.currentChange(this.currentPage);
            },

            beforeGetData: function () {

                this.getParams["plan_date"] = this.plan_date;
                this.getParams["equip_no"] = this.equip_no;
                this.getParams["product_no"] = this.stage_product_batch_no
            },
            planTrainsChangeForUpdate: function (index) {

                this.rubberDailyPlanChangeForm
                    .pdp_product_classes_plan[index].weight =
                    this.batching_weight_for_update * this.rubberDailyPlanChangeForm
                        .pdp_product_classes_plan[index].plan_trains;
                var time = this.batching_time_interval_for_update.split(":");
                var second = Number(time[2]) + Number(time[1]) * 60 + Number(time[0]) * 60 * 60;
                second = this.rubberDailyPlanChangeForm
                    .pdp_product_classes_plan[index].plan_trains * second;
                var date = new Date(null);
                date.setSeconds(second);
                this.rubberDailyPlanChangeForm.pdp_product_classes_plan[index].time =
                    date.toISOString().substr(11, 8);
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
            changePlan: function () {

                if (!this.currentRow) {

                    this.$alert("请选择修改行", '修改计划', {
                        confirmButtonText: '确定',
                    });
                    return;
                }
                var app = this;
                this.rubberDailyPlanChangeForm["plan_date"] = this.plan_date;
                axios.put(ProductDayPlansUrl + this.currentRow.id + "/",
                    this.rubberDailyPlanChangeForm).then(function (response) {

                    app.$message("创建成功");
                    app.currentChange(app.currentPage);
                }).catch(function (error) {

                    var text = "";
                    for (var key in error.response.data) {

                        text += error.response.data[key] + "\n";
                    }
                    app.$message(text);

                })
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
                if (!val)
                    return;
                this.rubberDailyPlanChangeForm.equip = this.currentRow.equip;
                this.rubberDailyPlanChangeForm.product_batching
                    = this.currentRow.product_batching;
                this.batching_weight_for_update = this.currentRow.batching_weight;
                this.batching_time_interval_for_update = this.currentRow.batching_time_interval;
                for (var i = 0; i < this.currentRow.pdp_product_classes_plan.length; ++i) {

                    for (var key in this.currentRow.pdp_product_classes_plan[i]) {

                        this.rubberDailyPlanChangeForm.pdp_product_classes_plan[i][key] =
                            this.currentRow.pdp_product_classes_plan[i][key];
                    }
                }
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
            },
            copyPlan: function () {

                var app = this;
                axios.post(ProductDayPlansCopyUrl, {
                        src_date: app.src_date,
                        dst_date: app.dst_date
                    }
                ).then(function (response) {

                    app.$message({
                        type: 'success',
                        message: '复制成功!'
                    });
                    app.currentChange(app.currentPage);
                    app.dialogCopyVisible = false
                }).catch(function (error) {

                    app.$message.error(JSON.stringify(error.response.data));
                });
            },
            addOnePlan() {

                if (!this.equipIdForAdd) {
                    return;
                }
                var pdp_product_classes_plan = [];
                for (var i = 0; i < 3; i++) {

                    pdp_product_classes_plan.push({
                        plan_trains: 0,
                        sn: 0,
                        unit: "吨",
                        time: 0,
                        weight: 0,
                    })
                }
                var plan =
                    {
                        equip_: this.equipById[this.equipIdForAdd],
                        equip: this.equipIdForAdd,
                        plan_date: this.plan_date,
                        pdp_product_classes_plan
                    };
                if (this.equipFirstIndexInPlansForAdd() === -1) {

                    this.plansForAdd.push(plan);
                    var planForSum = JSON.parse(JSON.stringify(plan));
                    planForSum["sum"] = true;
                    planForSum["equip_"].equip_no = "小计";
                    this.plansForAdd.push(planForSum)
                } else {

                    var lastIndex = this.equipLastIndexInPlansForAdd();
                    this.plansForAdd.splice(lastIndex, 0, plan)
                }
            },
            equipLastIndexInPlansForAdd() {

                for (var i = 0; i < this.plansForAdd.length; i++) {

                    if (this.plansForAdd[i].equip_.id === this.equipIdForAdd) {

                        var last = true;
                        for (var j = i + 1; j < this.plansForAdd.length; j++) {

                            if (this.plansForAdd[j] === this.equipIdForAdd)
                                last = false
                        }
                        if (last)
                            return i;
                    }
                }
                return -1;
            },
            equipFirstIndexInPlansForAdd() {

                for (var i = 0; i < this.plansForAdd.length; i++) {

                    if (this.plansForAdd[i].equip_.id === this.equipIdForAdd)
                        return i
                }
                return -1;
            },
            productBatchingChanged(planForAdd) {

                planForAdd["batching_weight"] = this.productBatchingById[planForAdd.product_batching].batching_weight;
                planForAdd["production_time_interval"] = this.productBatchingById[planForAdd.product_batching].production_time_interval;
                for (var i = 0; i < 3; i++) {
                    this.planTrainsChanged(planForAdd, i)
                }
            },
            planTrainsChanged(planForAdd, columnIndex) {

                planForAdd["pdp_product_classes_plan"][columnIndex]["time"] =
                    (planForAdd["production_time_interval"]
                        * planForAdd["pdp_product_classes_plan"][columnIndex]["plan_trains"]).toFixed(2);

                planForAdd["pdp_product_classes_plan"][columnIndex]["weight"] =
                    (planForAdd["batching_weight"]
                        * planForAdd["pdp_product_classes_plan"][columnIndex]["plan_trains"]).toFixed(2);
                this.statistic();
            },
            statistic() {

                var plansByEquip = {};
                var planSumByEquipId = {};
                this.plansForAdd.forEach(function (plan) {

                    if (!plan.sum) {

                        if (!plansByEquip[plan.equip]) {

                            plansByEquip[plan.equip] = []
                        }
                        plansByEquip[plan.equip].push(plan);
                    } else {
                        planSumByEquipId[plan.equip] = plan;
                    }
                });
                for (var equipId in plansByEquip) {

                    var plans = plansByEquip[equipId];
                    var batching_weight = 0;
                    var production_time_interval = 0;
                    var pdp_product_classes_plan = [];
                    for (var i = 0; i < 3; i++) {

                        pdp_product_classes_plan.push({
                            plan_trains: 0,
                            weight: 0,
                            time: 0,
                        })
                    }
                    plans.forEach(function (plan) {

                        batching_weight += Number(plan.batching_weight);
                        production_time_interval += Number(plan.production_time_interval);
                        for (var i = 0; i < 3; i++) {

                            var class_plan = plan.pdp_product_classes_plan[i];
                            pdp_product_classes_plan[i].plan_trains += Number(class_plan.plan_trains);
                            pdp_product_classes_plan[i].weight += Number(class_plan.weight);
                            pdp_product_classes_plan[i].time += Number(class_plan.time);
                        }
                    });
                    for (i = 0; i < 3; i++) {

                        pdp_product_classes_plan[i].weight = pdp_product_classes_plan[i].weight.toFixed(2);
                        pdp_product_classes_plan[i].time = pdp_product_classes_plan[i].time.toFixed(2);
                    }
                    batching_weight = batching_weight.toFixed(3);
                    production_time_interval = production_time_interval.toFixed(2);
                    var equip = this.equipById[equipId];
                    planSumByEquipId[equipId].batching_weight = batching_weight;
                    planSumByEquipId[equipId].production_time_interval = production_time_interval;
                    planSumByEquipId[equipId].pdp_product_classes_plan = pdp_product_classes_plan;
                }
            },
            batchSave() {

                var app = this;
                var plansForAdd_ = [];
                this.plansForAdd.forEach(function (plan) {

                    if (!plan.sum) {

                        plansForAdd_.push(plan)
                    }
                });
                axios.post(ProductDayPlanManyCreateUrl, plansForAdd_)
                    .then(function (response) {

                        app.addPlanVisible = false;
                        app.$message("创建成功");
                        app.currentChange(app.currentPage);
                    }).catch(function (error) {

                    app.$message(JSON.stringify(error.response.data));
                    //
                    // var text = "";
                    // for (var key in error.response.data) {
                    //
                    //     text += error.response.data[key] + "\n";
                    // }
                    // app.$message(text);
                });
            },
            arraySpanMethod({row, column, rowIndex, columnIndex}) {

            },
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();