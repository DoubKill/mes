;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {

            return {

                tableDataUrl: ProductActualUrl,
                performanceDate: dayjs("2020-08-07").format("YYYY-MM-DD"),
                projectName: "",
                equipNo: "",
                equipNoOptions: [],
                dialogAddMaterialBaseInfoVisible: false,
                materialBaseInfoForm: {

                    material_no: "",
                    material_name: "",
                    for_short: "",
                    density: null,
                    used_flag: false,
                    material_type: null,
                    package_unit: null
                },
                getDetailsParams: {},
                dialogVisibleRubber: false,
                tableDataRubber: [],
                tableDataBAT:[],
                dialogVisibleBAT: false,
                getBATParams: {},
                dialogVisibleGraph: false,
                option1: {
                     title: {
                         text: '折线图堆叠',
                         // left: "center",
                     },
                    tooltip: {
                        trigger: 'axis'
                    },
                    legend: {
                         // icon:'circle',
                         selectedMode: 'single',//单选
                        // data: ['温度', '功率', '能量', '压力', '转速']
                    },
                    grid: {
                         // show: true,
                        left: '5%',
                        right: '8%',
                        bottom: '5%',
                        containLabel: true
                    },
                    toolbox: {
                        // left: 'center',
                        feature: {
                            dataZoom: {
                                yAxisIndex: 'none'
                            },
                            restore: {},
                            saveAsImage: {}
                        }
                    },
                    xAxis: {
                         name: '车次',
                        // nameLocation: 'start',
                        nameTextStyle: {
                             fontWeight: 'bold',
                             fontSize: 18
                        },
                        type: 'category',
                        boundaryGap: false,
                        data: ['一', '二', '三', '四', '五', '六', '七']
                    },
                    yAxis: [{
                             position:'left',
                            type: 'value',
                            axisLabel: {
                                formatter: '{value} ℃'
                            }
                        },
                        {
                            position:'left',
                            type: 'value',
                            axisLabel: {
                                formatter: '{value} W'
                            }
                        },
                        {
                            position:'left',
                            type: 'value',
                            axisLabel: {
                                formatter: '{value} J'
                            }
                        },
                        {
                            position:'left',
                            type: 'value',
                            axisLabel: {
                                formatter: '{value} Pa'
                            }
                        },
                        {
                            position:'left',
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
                            yAxisIndex:'0',
                            data: [120, 132, 101, 134, 90, 230, 210],
                            // markLine: {
                            //     silent: true,
                            //     data: [{
                            //         yAxis: 50
                            //     }, {
                            //         yAxis: 100
                            //     }, {
                            //         yAxis: 150
                            //     }, {
                            //         yAxis: 200
                            //     }, {
                            //         yAxis: 300
                            //     }]
                            // }
                        },
                        {
                            name: '功率',
                            type: 'line',
                            smooth: true,
                            stack: '总量',
                            yAxisIndex:'1',
                            data: [220, 182, 191, 234, 290, 330, 310],
                            // markLine: {
                            //     silent: true,
                            //     data: [{
                            //         yAxis: 50
                            //     }, {
                            //         yAxis: 100
                            //     }, {
                            //         yAxis: 150
                            //     }, {
                            //         yAxis: 200
                            //     }, {
                            //         yAxis: 300
                            //     }]
                            // }
                        },
                        {
                            name: '能量',
                            type: 'line',
                            smooth: true,
                            stack: '总量',
                            yAxisIndex:'2',
                            data: [150, 232, 201, 154, 190, 330, 410]
                        },
                        {
                            name: '压力',
                            type: 'line',
                            smooth: true,
                            stack: '总量',
                            yAxisIndex:'3',
                            data: [320, 332, 301, 334, 390, 330, 320]
                        },
                        {
                            name: '转速',
                            type: 'line',
                            smooth: true,
                            stack: '总量',
                            yAxisIndex:'4',
                            data: [820, 932, 901, 934, 1290, 1330, 1320]
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
            showAddDialog() {
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
            clickBAT(row) {
                this.getBATParams['product_no'] = row.product_no
                this.getBATParams['equip_no'] = row.equip_no
                const app = this;
                axios.get(this.TrainsFeedbacksUrl, {
                    params: this.getBATParams
                }).then(function (response) {

                    app.tableDataBAT = response.data.results;

                }).catch(function (error) {
                });
                this.dialogVisibleBAT = true
            },
            opens () {
                this.$nextTick(() => {
                    this.pie1()
                })
            },
            pie1(){
                echarts.init(this.$refs.main).setOption(this.option1)
            },
            viewGraph() {
                this.dialogVisibleGraph = true;
            }

        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();