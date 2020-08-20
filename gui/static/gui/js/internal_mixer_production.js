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
                tableDataUrl: InternalMixerUrl,
                tableData: [],
                search_date: [],
                getParams: {
                    page: 1,
                    equip_no: null,
                    product_no: null,
                    plan_classes_uid: null,
                    st: '',
                    et: ''
                },
                normsList: [],
                produceList: [],
                groupList: [],
                dialogVisibleRubber: false,
                tableDataRubber: [],
                tableDataBAT: [],
                dialogVisibleBAT: false,
                glueList: [],
                machineList: [],
                classesList: [],
                //24小时，转换为时间戳24*60*60*1000
                fixedTime: 24 * 60 * 60 * 1000,
                palletFeedObj: {},
                palletFeedList: [],
                BATObj: {},
                BATList: [],
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
        created() {
            this.getList()
            this.getGlueList()  //获取胶料列表
            this.getMachineList()  //获取机台列表
            this.getClassesList()   //获取班次列表

            var _setDateCurrent = setDate()
            // this.getParams.st = _setDateCurrent + " 00:00:00"
            // this.getParams.et = _setDateCurrent + ' 23:59:59'
            // this.search_date = [this.getParams.st, this.getParams.et]
            this.getParams.st = '2020-06-01' + " 00:00:00"
            this.getParams.et = '2020-06-01' + ' 23:59:59'
            this.search_date = [this.getParams.st, this.getParams.et]
        },
        methods: {
            getList() {
                var _this = this
                axios.get(_this.tableDataUrl, {
                    params: _this.getParams
                }).then(function (response) {
                    _this.tableData = response.data.results || [];
                    if (_this.tableDataTotal !== response.data.count) {
                        _this.tableDataTotal = response.data.count;
                    }
                }).catch(function (error) {
                    this.$message.error('请求错误')
                });
            },
            getGlueList() {
                var _this = this
                axios.get(RubberMaterialUrl, {
                    params: {
                        page_size: 10000000
                    }
                }).then(function (response) {
                    var glueList = response.data.results || [];
                    //去重
                    var obj = {}
                    var newArr = glueList.reduce(function (item, next) {
                        obj[next.product_name] ? ' ' : obj[next.product_name] = true && item.push(next)
                        return item;
                    }, [])
                    _this.glueList = newArr
                }).catch(function (error) {
                });
            },
            getMachineList() {
                var _this = this
                axios.get(EquipUrl, {params: {page_size: 1000000}}).then(function (response) {
                    _this.machineList = response.data.results || [];
                }).catch(function (error) {
                });
            },
            getClassesList() {
                var _this = this
                axios.get(ClassesListUrl).then(function (response) {
                    _this.classesList = response.data.results || [];
                }).catch(function (error) {
                });
            },
            clickPrint() {
                //          <el-form-item>
                //     <el-button @click="clickPrint">
                //         下载
                //     </el-button>
                // </el-form-item>
                // <el-form-item>
                //     <el-button @click="clickExcel">
                //         Excel
                //     </el-button>
                // </el-form-item>
            },
            clickExcel() {
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
                        plan_classes_uid: _this.palletFeedObj.plan_classes_uid,
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
            changeSearch() {
                console.log(this.search_date)
                if (this.search_date) {
                    this.getParams.st = this.search_date[0]
                    this.getParams.et = this.search_date[1]
                }

                this.getParams.page = 1
                this.getList()
            },
            setEndTime(val) {
                var end_time = (new Date(val)).getTime()
                var add = end_time + this.fixedTime
                return setDate(add, true)
            },
            opens() {
                this.$nextTick(() => {
                    echarts.init(this.$refs.main).setOption(this.option1)
                })
            }
        }
    }
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")

    function setDate(_data, bool) {
        var date = _data ? new Date(_data) : new Date()
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
            return formatObj.y + '-' + formatObj.m + '-' + formatObj.d + ' ' +
                formatObj.h + ':' + formatObj.i + ':' + formatObj.s
        } else {
            return formatObj.y + '-' + formatObj.m + '-' + formatObj.d
        }
    }
})();