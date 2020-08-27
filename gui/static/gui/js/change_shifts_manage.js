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
                rules: {
                    schedule_no: [
                        {required: true, message: '请输入倒班代码', trigger: 'blur'}
                    ],
                    schedule_name: [
                        {required: true, message: '请输入倒班名', trigger: 'blur'}
                    ]
                }
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
                this.changeShiftsManageForm.classesdetail_set[0].times = [
                    new Date(),
                    new Date()
                ]
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
                console.log(this.workSchedules)
            },
            showDialogCreateChangeShiftsManage() {

                this.initChangeShiftsManageForm();
                this.dialogCreateChangeShiftsManageVisible = true;
            },
            format(date) {
                if (!date) {
                    return ''
                }
                return dayjs(date).format("HH:mm:ss")
            },
            adjustTimes() {
                var _this = this
                this.changeShiftsManageForm.classesdetail_set.forEach(function (data, index) {
                    data.start_time = data.times && data.times.length > 0 ? _this.format(data.times[0]) : ''
                    data.end_time = data.times && data.times.length > 0 ? _this.format(data.times[1]) : ''
                })
                // for (var i = 0; i < this.changeShiftsManageForm.classesdetail_set.length; ++i) {
                //     this.changeShiftsManageForm.classesdetail_set[i]['start_time'] = this.format(this.changeShiftsManageForm.classesdetail_set[i].times[0]);
                //     this.changeShiftsManageForm.classesdetail_set[i]['end_time'] = this.format(this.changeShiftsManageForm.classesdetail_set[i].times[1]);
                // }
            },
            handleCreateChangeShifts() {
                var app = this;
                this.$refs['shiftsManageForm'].validate(function (valid) {
                    if (valid) {
                        app.clearChangeShiftsManageFormError();
                        app.adjustTimes();
                        var obj = {}
                        obj = JSON.parse(JSON.stringify(app.changeShiftsManageForm))
                        let newarr = obj.classesdetail_set.filter(function (data, index) {
                            return data.times && data.times.length > 1
                        })
                        if (newarr.length === 0 || !newarr) {
                            app.$message.info('请填写一个班次')
                            return
                        }
                        obj.classesdetail_set = newarr

                        axios.post(WorkSchedulesUrl, obj)
                            .then(function (response) {

                                app.dialogCreateChangeShiftsManageVisible = false;
                                app.$message.success(app.changeShiftsManageForm.schedule_name + "创建成功");
                                app.currentChange(app.currentPage);
                            }).catch(function (error) {

                            app.$message.error(JSON.stringify(error.response.data));
                            for (var key in app.changeShiftsManageFormError) {
                                if (error.response.data[key])
                                    app.changeShiftsManageFormError[key] = error.response.data[key].join(",")
                            }
                        });
                    } else {
                        return false;
                    }
                });
            },
            showEditChangeShiftsManageDialog(workSchedule) {

                this.clearChangeShiftsManageFormError();
                // this.changeShiftsManageForm = Object.assign({}, workSchedule);
                this.changeShiftsManageForm = JSON.parse(JSON.stringify(workSchedule));
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
                console.log(this.changeShiftsManageForm.classesdetail_set)
                for (var i = 0; i < this.changeShiftsManageForm.classesdetail_set.length; ++i) {

                    if (this.changeShiftsManageForm.classesdetail_set[i].times) {
                        this.changeShiftsManageForm.classesdetail_set[i]['start_time'] = this.changeShiftsManageForm.classesdetail_set[i].times[0];
                        this.changeShiftsManageForm.classesdetail_set[i]['end_time'] = this.changeShiftsManageForm.classesdetail_set[i].times[1];
                    }
                    else {
                        this.changeShiftsManageForm.classesdetail_set.splice(i, 1)
                    }
                }
                axios.put(WorkSchedulesUrl + this.changeShiftsManageForm.id + "/", this.changeShiftsManageForm)
                    .then(function (response) {

                        app.dialogEditChangeShiftsManageVisible = false;
                        app.$message(app.changeShiftsManageForm.schedule_name + "修改成功");
                        app.currentChange(app.currentPage);
                    }).catch(function (error) {

                    app.$message.error(error.response.data.join(","));
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

                var class_name = '晚班';
                switch (index) {
                    case 0:
                        class_name = '早班';
                        break;
                    case 1:
                        class_name = '中班';
                        break
                }
                var classesdetail = workSchedule.classesdetail_set.find(detail => {
                    return detail.classes_name === class_name
                });
                if (classesdetail) {
                    return classesdetail[key]
                }
            }
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount('#app')

})();