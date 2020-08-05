;(function () {

    var Main = {

        mixins: [BaseMixin],
        data: function () {

            return {

                startTime: Date.now(),
                workSchedules: [],
                workScheduleOptions: [],
                workScheduleIndex: null,
                classData: [],
                groups: [],
                groupById: {},
                groupIds: [],

                changeShiftsPeriods: [],
                changeShiftsPeriod: null,
                scheduleData: [],
                classes: [],
                fullscreenLoading: false
            }
        },
        methods: {

            dayOfWeek(day) {

                switch (day) {

                    case 0:
                        return "天";
                    case 1:
                        return "一";
                    case 2:
                        return "二";
                    case 3:
                        return "三";
                    case 4:
                        return "四";
                    case 5:
                        return "五";
                    case 6:
                        return "六";
                }
            },
            generateScheduling() {

                this.groupIds = [];
                for (var i = 0;
                     i < this.workSchedules[this.workScheduleIndex].classesdetail_set.length; ++i) {
                    this.groupIds.push(this.workSchedules[this.workScheduleIndex].classesdetail_set[i].group);
                }
                this.scheduleData = [];
                var date = dayjs(this.startTime);
                for (var j = 0; j < 360; ++j) {

                    var day = date.get('day');
                    var row = {

                        production_time: date.format('YYYY-MM-DD'),
                        day_of_the_week: "星期" + this.dayOfWeek(day),
                        group_infos: []
                    };
                    for (var k = 0; k < this.groupIds.length; ++k) {


                        row['group_infos'].push({
                                group_id: this.groupIds[k],
                                group_name: this.groupById[this.groupIds[k]],
                                start_time: this.classData[k].start_time,
                                end_time: this.classData[k].end_time,
                                is_rest: false
                            }
                        )
                    }
                    if ((j + 1) % Number(this.changeShiftsPeriod) === 0) {

                        var id = this.groupIds.pop();
                        this.groupIds.unshift(id)
                    }
                    this.scheduleData.push(row);
                    date = date.add(1, 'day');
                }
            },
            shiftsTimeChange() {

                this.classData = this.workSchedules[this.workScheduleIndex].classesdetail_set;
            }
        },
        created: function () {

            var app = this;
            axios.get(GlobalCodesUrl, {

                params: {

                    class_name: "倒班周期"
                }
            }).then(function (response) {

                app.changeShiftsPeriods = response.data.results;
            }).catch(function (error) {

            });
            axios.get(GlobalCodesUrl, {

                params: {

                    class_name: "班组"
                }
            }).then(function (response) {

                app.groups = response.data.results;
                for (var i = 0; i < app.groups.length; ++i) {

                    app.groupById[app.groups[i].id] = app.groups[i].global_name;
                }
            }).catch(function (error) {

            });
            axios.get(GlobalCodesUrl, {

                params: {

                    class_name: "班次"
                }
            }).then(function (response) {

                app.classes = response.data.results;
            }).catch(function (error) {

            });
            axios.get(WorkSchedulesUrl)
                .then(function (response) {

                    app.workSchedules = response.data.results;
                    for (var i = 0; i < app.workSchedules.length; ++i) {

                        app.workSchedules[i]["group"] = "";
                        var label = app.workSchedules[i].classesdetail_set.length + "班次";
                        for (var j = 0; j < app.workSchedules[i].classesdetail_set.length; ++j) {

                            label += "[" + (j + 1) + "]"
                                + "-"
                                + app.workSchedules[i].classesdetail_set[j].start_time
                                + "/"
                                + app.workSchedules[i].classesdetail_set[j].end_time;
                        }
                        app.workScheduleOptions.push({

                            value: i,
                            label
                        });
                    }
                }).catch(function (error) {

            })
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();
