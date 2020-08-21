;(function () {


    var Main = {

        mixins: [BaseMixin],
        data: function () {

            return {

                tableDataUrl: WorkSchedulesUrl,
                workSchedules: [],
                dialogCreateChangeShiftsManageVisible: false,
                dialogEditChangeShiftsManageVisible: false,
                changeShiftsManageForm: {

                    schedule_no: "",
                    schedule_name: "",
                    description: "",
                    period: 0,
                    classesdetail_set: [{
                        times: [new Date(),
                            new Date()],
                        description: "",
                        classes_name: "",
                        classes: null
                    }
                    ]
                },
                changeShiftsManageFormError: {

                    schedule_no: "",
                    schedule_name: "",
                    description: "",
                },
                classes: [],
            }
        },
        created: function () {

            var app = this;
            axios.get(GlobalCodesUrl, {

                params: {
                    class_name: "班次"
                }
            }).then(function (response) {

                app.classes = response.data.results;
            }).catch(function (error) {

            })
        },
        methods: {

            initChangeShiftsManageForm() {

                this.changeShiftsManageForm = {

                    schedule_no: "",
                    schedule_name: "",
                    description: "",
                    period: 0,
                    classesdetail_set: []
                };
                for (var i = 0; i < this.classes.length; ++i) {

                    this.changeShiftsManageForm.classesdetail_set.push({

                        times: [new Date(),
                            new Date()],
                        description: "",
                        classes_name: this.classes[i].global_name,
                        classes: this.classes[i].id
                    })
                }
            },
            clearChangeShiftsManageFormError() {

                this.changeShiftsManageFormError = {

                    schedule_no: "",
                    schedule_name: "",
                    description: "",
                };
            },
            afterGetData: function () {

                this.workSchedules = this.tableData;
            },
            showDialogCreateChangeShiftsManage() {

                this.initChangeShiftsManageForm();
                this.dialogCreateChangeShiftsManageVisible = true;
            },
            format(date) {

                return dayjs(date).format("HH:mm:ss")
            },
            adjustTimes() {

                for (var i = 0; i < this.changeShiftsManageForm.classesdetail_set.length; ++i) {

                    this.changeShiftsManageForm.classesdetail_set[i]['start_time'] = this.format(this.changeShiftsManageForm.classesdetail_set[i].times[0]);
                    this.changeShiftsManageForm.classesdetail_set[i]['end_time'] = this.format(this.changeShiftsManageForm.classesdetail_set[i].times[1]);
                }
            },
            handleCreateChangeShifts() {

                this.clearChangeShiftsManageFormError();
                this.adjustTimes();
                var app = this;
                axios.post(WorkSchedulesUrl, this.changeShiftsManageForm)
                    .then(function (response) {

                        app.dialogCreateChangeShiftsManageVisible = false;
                        app.$message(app.changeShiftsManageForm.schedule_name + "创建成功");
                        app.currentChange(app.currentPage);
                    }).catch(function (error) {

                    app.$message.error(JSON.stringify(error.response.data));
                    for (var key in app.changeShiftsManageFormError) {
                        if (error.response.data[key])
                            app.changeShiftsManageFormError[key] = error.response.data[key].join(",")
                    }
                });
            },
            showEditChangeShiftsManageDialog(workSchedule) {

                this.clearChangeShiftsManageFormError();
                this.changeShiftsManageForm = Object.assign({}, workSchedule);
                for (var i = 0; i < this.changeShiftsManageForm.classesdetail_set.length; ++i) {

                    Vue.set(this.changeShiftsManageForm.classesdetail_set[i], "times", [

                            this.changeShiftsManageForm.classesdetail_set[i].start_time,
                            this.changeShiftsManageForm.classesdetail_set[i].end_time]);
                }
                this.dialogEditChangeShiftsManageVisible = true;
            },
            handleEditChangeShifts() {

                this.clearChangeShiftsManageFormError();
                var app = this;
                for (var i = 0; i < this.changeShiftsManageForm.classesdetail_set.length; ++i) {

                    this.changeShiftsManageForm.classesdetail_set[i]['start_time'] = this.changeShiftsManageForm.classesdetail_set[i].times[0];
                    this.changeShiftsManageForm.classesdetail_set[i]['end_time'] = this.changeShiftsManageForm.classesdetail_set[i].times[1];
                }
                axios.put(WorkSchedulesUrl + this.changeShiftsManageForm.id + "/", this.changeShiftsManageForm)
                    .then(function (response) {

                        app.dialogEditChangeShiftsManageVisible = false;
                        app.$message(app.changeShiftsManageForm.schedule_name + "修改成功");
                        app.currentChange(app.currentPage);
                    }).catch(function (error) {

                    for (var key in app.changeShiftsManageFormError) {
                        if (error.response.data[key])
                            app.changeShiftsManageFormError[key] = error.response.data[key].join(",")
                    }
                });
            },
            handleDeleteChangeShiftsManage(workSchedule) {

                var app = this;
                this.$confirm('此操作将永久删除' + workSchedule.schedule_name + ', 是否继续?', '提示', {
                    confirmButtonText: '确定',
                    cancelButtonText: '取消',
                    type: 'warning'
                }).then(() => {

                    axios.delete(WorkSchedulesUrl + workSchedule.id + '/')
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
            getCellText(workSchedule, index, key) {

                if (workSchedule.classesdetail_set &&
                    index < workSchedule.classesdetail_set.length
                    && workSchedule.classesdetail_set[index][key])
                    return workSchedule.classesdetail_set[index][key];
            }
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount('#app')

})();