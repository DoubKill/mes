;(function () {
    var echartsTime = []
    var echartsTemprature = []
    var echartsPower = []
    var echartsEnergy = []
    var echartsPressure = []
    var echartsRpm = []
    var Main = {
        mixins: [BaseMixin],
        data: function () {

            return {

                tableDataUrl: ProductActualUrl,
                performanceDate: dayjs("2020-01-01").format("YYYY-MM-DD"),
                projectName: "",
                equipNo: "",
                equipNoOptions: [],
                dialogAddMaterialBaseInfoVisible: false,
                // materialBaseInfoForm: {
                //
                //     material_no: "",
                //     material_name: "",
                //     for_short: "",
                //     density: null,
                //     used_flag: false,
                //     material_type: null,
                //     package_unit: null
                // },
                // getParams: {
                //     page: 1,
                //     equip_no: null,
                //     product_no: null,
                //     plan_classes_uid: null,
                //     st: '',
                //     et: ''
                // },
                palletFeedObj: {},
                palletFeedList: [],
                BATObj: {},
                BATList: [],
                dialogVisibleRubber: false,
                tableDataRubber: [],
                tableDataBAT:[],
                dialogVisibleBAT: false,
                dialogVisibleGraph: false,
                option1: {
                    title: {
                        text: '折线图堆叠'
                    },
                    tooltip: {
                        trigger: 'axis'
                    },
                    legend: {
                        selectedMode: 'single',//单选
                    },
                    grid: {
                        left: '5%',
                        right: '8%',
                        bottom: '5%',
                        containLabel: true
                    },
                    toolbox: {
                        feature: {
                            dataZoom: {
                                yAxisIndex: 'none'
                            },
                            restore: {},
                            saveAsImage: {}
                        }
                    },
                    xAxis: {
                        name: '时间',
                        // nameLocation: 'start',
                        nameTextStyle: {
                            fontWeight: 'bold',
                            fontSize: 12
                        },
                        type: 'category',
                        boundaryGap: false,
                        data: echartsTime
                    },
                    yAxis: [{
                        position: 'left',
                        type: 'value',
                        axisLabel: {
                            formatter: '{value} ℃'
                        }
                    },
                        {
                            position: 'left',
                            type: 'value',
                            axisLabel: {
                                formatter: '{value} W'
                            }
                        },
                        {
                            position: 'left',
                            type: 'value',
                            axisLabel: {
                                formatter: '{value} J'
                            }
                        },
                        {
                            position: 'left',
                            type: 'value',
                            axisLabel: {
                                formatter: '{value} Pa'
                            }
                        },
                        {
                            position: 'left',
                            type: 'value',
                            axisLabel: {
                                formatter: '{value} rps'
                            }
                        },
                    ],
                    series: [
                        {
                            name: '温度',
                            type: 'line',
                            smooth: true,
                            stack: '总量',
                            yAxisIndex: '0',
                            data: echartsTemprature
                        },
                        {
                            name: '功率',
                            type: 'line',
                            smooth: true,
                            stack: '总量',
                            yAxisIndex: '1',
                            data: echartsPower
                        },
                        {
                            name: '能量',
                            type: 'line',
                            smooth: true,
                            stack: '总量',
                            yAxisIndex: '2',
                            data: echartsEnergy
                        },
                        {
                            name: '压力',
                            type: 'line',
                            smooth: true,
                            stack: '总量',
                            yAxisIndex: '3',
                            data: echartsPressure
                        },
                        {
                            name: '转速',
                            type: 'line',
                            smooth: true,
                            stack: '总量',
                            yAxisIndex: '4',
                            data: echartsRpm
                        }
                    ]
                }
            }
        },
        created: function () {

            var app = this;
            axios.get(GlobalCodesUrl, {

                params: {

                    class_name: "机台"
                }
            }).then(function (response) {

                app.equipNoOptions = response.data.results;
            }).catch(function (error) {

            });
            console.log(app.tableData);
        },
        methods: {
            downloadClick(rew) {
            },
            performanceDateChange() {
                this.getFirstPage();
            },
            materialNameChanged() {
                this.getFirstPage();
            },
            equipNoChange() {
                this.getFirstPage();
            },
            clickProductNo(row) {
                this.dialogVisibleRubber = true
                this.palletFeedObj = row
                this.getRubberCoding()
            },
            getRubberCoding() {
                var _this = this
                axios.get(PalletFeedBacksUrl, {
                    params: {
                        product_no: _this.palletFeedObj.product_no,
                        // plan_classes_uid: _this.palletFeedObj.plan_classes_uid,
                        equip_no: _this.palletFeedObj.equip_no
                    }
                }).then(function (response) {
                    _this.palletFeedList = response.data.results || [];
                }).catch(function (error) {
                });
            },
            clickBAT(row) {
                this.dialogVisibleBAT = true
                this.BATObj = row
                this.getBATList()
            },
            getBATList() {
                var _this = this
                axios.get(TrainsFeedbacksUrl, {
                    params: {
                        plan_classes_uid: _this.BATObj.plan_classes_uid,
                        equip_no: _this.BATObj.equip_no,
                        actual_trains: _this.BATObj.begin_trains + ',' + _this.BATObj.end_trains
                    }
                }).then(function (response) {
                    _this.BATList = response.data.results || [];
                }).catch(function (error) {
                });
            },
            viewGraph() {
                this.dialogVisibleGraph = true
                this.getEchartsList()
            },
            getEchartsList() {
                var _this = this
                axios.get(EchartsListUrl, {
                    params: {
                        product_no: _this.BATObj.product_no,
                        plan_classes_uid: _this.BATObj.plan_classes_uid,
                        equip_no: _this.BATObj.equip_no,
                        actual_trains: _this.BATObj.begin_trains + ',' + _this.BATObj.end_trains
                    }
                }).then(function (response) {
                    var results = response.data.results
                    results.forEach(function (D) {
                        var created_date = D.created_date.split(' ')[1]
                        echartsTime.push(created_date)
                        echartsTemprature.push(D.temperature)
                        echartsPower.push(D.power)
                        echartsEnergy.push(D.energy)
                        echartsPressure.push(D.pressure)
                        echartsRpm.push(D.rpm)
                    })
                }).catch(function (error) {
                });
            },
            currentChange: function (page) {

            this.beforeGetData();
            this.getParams["page"] = page;
            this.tableData = [];
            const app = this;
            axios.get(this.tableDataUrl, {

                params: this.getParams
            }).then(function (response) {

                if (app.tableDataTotal !== response.data.count) {
                    app.tableDataTotal = response.data.count;
                }
                app.tableData = response.data.data;
                app.afterGetData();

            }).catch(function (error) {
                // this.$message.error(error);
            })
            },
            beforeGetData() {
                this.getParams["search_time"] = dayjs(this.performanceDate).format("YYYY-MM-DD");
                this.getParams["equip_no"] = this.equipNo
            },
            detailsClick(row) {

                this.getDetailsParams['product_no'] = row.product_no
                this.getDetailsParams['equip_no'] = row.equip_no
                const app = this;
                axios.get(this.PalletFeedbacksUrl, {
                    params: this.getDetailsParams
                }).then(function (response) {

                    app.tableDataRubber = response.data.results;

                }).catch(function (error) {
                });
                this.dialogVisibleRubber = true
            },

            // clickBAT(row) {
            //     this.getBATParams['product_no'] = row.product_no
            //     this.getBATParams['equip_no'] = row.equip_no
            //     const app = this;
            //     axios.get(this.TrainsFeedbacksUrl, {
            //         params: this.getBATParams
            //     }).then(function (response) {
            //
            //         app.tableDataBAT = response.data.results;
            //
            //     }).catch(function (error) {
            //     });
            //     this.dialogVisibleBAT = true
            // },
            opens () {
                this.$nextTick(() => {
                    this.pie1()
                })
            },
            pie1(){
                echarts.init(this.$refs.main).setOption(this.option1)
            },
            // viewGraph() {
            //     this.dialogVisibleGraph = true;
            // }

        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();