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
                // productBatchings: [],
                productBatchingById: {},
                addPlanVisible: false,
                changePlanVisible: false,
                currentRow: null,
                dialogCopyVisible: false,
                src_date: null,
                dst_date: null,
                plansForAdd: [],
                statisticData: [],
                equipIdForAdd: null,
                planScheduleId: null,
                planSchedules: [],
                plan_date_for_create: dayjs().format("YYYY-MM-DD"),
                workSchedules: [],
                day_time: "",
                selectDateArr: []
            }
        },
        created: function () {

            this.selectDateArr = ['2020-8-5 11:20:00', '2020-8-7 11:20:00', '2020-8-15  11:20:00']
            this.selectDateArr = this.setTimeStamp(this.selectDateArr)

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
            axios.get(WorkSchedulesUrl, {
                params: {
                    all: 1
                }
            }).then(function (response) {

                app.workSchedules = response.data.results;
            }).catch(function (error) {

            })
        },
        methods: {

            getPlanSchedules() {

                var app = this;
                axios.get(PlanScheduleUrl, {

                    params: {
                        all: 1,
                        day_time: this.day_time
                    }
                }).then(function (response) {

                    app.planSchedules = response.data.results;
                    app.planScheduleId = null
                }).catch(function (error) {

                });
            },
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
            deleteOnePlan(plan) {

                this.plansForAdd.splice(this.plansForAdd.indexOf(plan), 1);
                var plans = this.plansForAdd.filter(plan_ => {
                    return plan_.equip === plan.equip
                });
                if (plans.length === 1 && plans[0].sum) {
                    this.plansForAdd.splice(this.plansForAdd.indexOf(plans[0]), 1);
                }
                this.statistic();
            },
            async addOnePlan() {

                if (!this.equipIdForAdd) {
                    return;
                }
                let res = await axios.get(PlanScheduleUrl + this.planScheduleId + "/");
                let planSchedule = res.data;
                var workSchedule = this.workSchedules.find(workSchedule => {

                    return workSchedule.id === planSchedule.work_schedule
                });
                if (!planSchedule.work_schedule_plan.length) {
                    this.$alert(planSchedule.work_schedule_name + '无排班', '错误', {
                        confirmButtonText: '确定',
                    });
                    return;
                }
                var classesdetail_set_ = workSchedule.classesdetail_set;
                var pdp_product_classes_plan = [];
                for (var i = 0; i < 3; i++) {

                    var enable = !!planSchedule.work_schedule_plan[i];
                    pdp_product_classes_plan.push({
                        plan_trains: 0,
                        sn: 0,
                        unit: "吨",
                        time: enable ? 0 : '',
                        weight: enable ? 0 : '',
                        classes: classesdetail_set_[i].classes,
                        enable
                    })
                }
                var plan =
                    {
                        equip_: this.equipById[this.equipIdForAdd],
                        equip: this.equipIdForAdd,
                        plan_schedule: this.planScheduleId,
                        pdp_product_classes_plan,
                    };
                var app = this;
                axios.get(RubberMaterialUrl, {
                    params: {
                        all: 1,
                        used_type: 4,
                        dev_type: app.equipById[app.equipIdForAdd].category
                    }
                }).then(function (response) {

                    Vue.set(plan, 'productBatchings', response.data.results);
                    response.data.results.forEach(function (batching) {
                        //
                        app.productBatchingById[batching.id] = batching;
                    })
                });

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
                    this.planTrainsChanged(planForAdd, i, false)
                }
                this.statistic();
            },
            planTrainsChanged(planForAdd, columnIndex, sum = true) {

                if (!planForAdd["pdp_product_classes_plan"][columnIndex].enable)
                    return;

                planForAdd["pdp_product_classes_plan"][columnIndex]["time"] =
                    (planForAdd["production_time_interval"]
                        * planForAdd["pdp_product_classes_plan"][columnIndex]["plan_trains"]).toFixed(2);

                planForAdd["pdp_product_classes_plan"][columnIndex]["weight"] =
                    (planForAdd["batching_weight"]
                        * planForAdd["pdp_product_classes_plan"][columnIndex]["plan_trains"]).toFixed(2);
                if (sum)
                    this.statistic();
            },
            async statistic() {

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
                    for (var j = 0; j < 3; j++) {

                        pdp_product_classes_plan.push({
                            plan_trains: 0,
                            weight: 0,
                            time: 0,
                        })
                    }
                    var app = this;
                    for (var k = 0; k < plans.length; k++) {

                        var plan = plans[k];
                        let res = await axios.get(PlanScheduleUrl + plan.plan_schedule + "/");
                        let planSchedule = res.data;
                        batching_weight += Number(plan.batching_weight);
                        production_time_interval += Number(plan.production_time_interval);
                        for (var i = 0; i < 3; i++) {

                            var class_plan = plan.pdp_product_classes_plan[i];
                            pdp_product_classes_plan[i].plan_trains += Number(class_plan.plan_trains);
                            pdp_product_classes_plan[i].weight += Number(class_plan.weight);
                            pdp_product_classes_plan[i].time += Number(class_plan.time);
                            var workSchedulePlanTimeSpan =
                                dayjs(planSchedule.work_schedule_plan[i].end_time).diff(
                                    dayjs(planSchedule.work_schedule_plan[i].start_time), "minute")
                            if (pdp_product_classes_plan[i].time > workSchedulePlanTimeSpan) {

                                app.$alert('机台' + plan.equip_.equip_no
                                    + planSchedule.work_schedule_plan[i].classes_name
                                    + '计划时间大于排班时间' + '(计划时间' + pdp_product_classes_plan[i].time + '分钟'
                                    + ' 排班时间' + workSchedulePlanTimeSpan + '分钟' +
                                    ')', '警告', {
                                    confirmButtonText: '确定',
                                });
                            }
                        }
                    }
                    // for (i = 0; i < 3; i++) {
                    //
                    //     pdp_product_classes_plan[i].weight = pdp_product_classes_plan[i].weight.toFixed(2);
                    //     pdp_product_classes_plan[i].time = pdp_product_classes_plan[i].time.toFixed(2);
                    // }

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

                        var plan_ = JSON.parse(JSON.stringify(plan));
                        plan_.pdp_product_classes_plan = [];
                        for (var i = 0; i < plan.pdp_product_classes_plan.length; i++) {

                            if (plan.pdp_product_classes_plan[i].enable) {
                                plan_.pdp_product_classes_plan.push(plan.pdp_product_classes_plan[i])
                            }
                        }
                        plansForAdd_.push(plan_)
                    }
                });
                if (!plansForAdd_.length)
                    return;

                axios.post(ProductDayPlanManyCreateUrl, plansForAdd_)
                    .then(function (response) {

                        app.addPlanVisible = false;
                        app.$message("创建成功");
                        app.currentChange(app.currentPage);
                    }).catch(function (error) {

                    error.response.data.forEach(function (err) {

                        if (err["pdp_product_classes_plan"]) {

                            for (var i = 0; i < err["pdp_product_classes_plan"].length; i++) {

                                if (err["pdp_product_classes_plan"][i].weight) {
                                    app.$alert(err["pdp_product_classes_plan"][i].weight.join(","), '错误', {
                                        confirmButtonText: '确定',
                                    });
                                }
                            }
                        }
                        if (err["product_batching"]) {
                            app.$alert("胶料配方编码是必填项。", '错误', {
                                confirmButtonText: '确定',
                            });
                        }
                    })


                });
            },
            arraySpanMethod({row, column, rowIndex, columnIndex}) {

            },
            sendToAu(plan) {

                var app = this;
                axios.post(ProductDayPlanNoticeUrl + plan.id).then(function (response) {

                    app.$message("发送成功");
                }).catch(function (error) {

                    app.$message("发送失败");
                });

                console.log(plan)
            },
            showAddPlansDialog() {

                this.plansForAdd = []
                this.addPlanVisible = true;
            },
            setTimeStamp() {
                const arr = []
                this.selectDateArr.forEach((D, index) => {
                    const startD = D.split(' ')[0]
                    arr[index] = (new Date(startD.replace(/-/g, '/'))).getTime()
                })
                return arr
            },
            _setDateModel(date, bool) {
                const currentDate = this.setDate(date, bool)
                const currentStamp = (new Date(currentDate.replace(/-/g, '/'))).getTime()
                const boolVal = this.selectDateArr.findIndex(D => D === currentStamp)
                return boolVal > -1
            },
            setDate(_data, bool) {
            const date = _data ? new Date(_data) : new Date()
            const formatObj = {
            y: date.getFullYear(),
            m: date.getMonth() + 1,
            d: date.getDate(),
            h: date.getHours(),
            i: date.getMinutes(),
            s: date.getSeconds(),
            a: date.getDay()
        }
        if (bool) {
            return formatObj.y + '-' + formatObj.m + '-' + formatObj.d + ' ' +
                formatObj.h + ':' + formatObj.i + ':' + formatObj.s
        } else {
            return formatObj.y + '-' + formatObj.m + '-' + formatObj.d
        }
    }
}
}
    ;
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();