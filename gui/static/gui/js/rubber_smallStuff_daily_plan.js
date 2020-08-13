;(function () {
    var unit = 'kg'
    var Main = {
        mixins: [BaseMixin],
        data: function () {
            return {
                tableDataUrl: ProductBatching,
                machineList: [],
                glueList: [],
                formCopyData: {
                    dst_date: null,
                    src_date: null
                },
                getParams: {plan_date: '', page: 1},
                copyDialogVisible: false,
                loadingBtnCopy: false,
                pickerOptionsCopy: {
                    disabledDate: this.disabledDate
                },
                manageFormError: {},
                rules: {
                    src_date: [
                        {required: true, message: '请选择来源日期', trigger: 'change'}
                    ],
                    dst_date: [
                        {required: true, message: '请选择新建日期', trigger: 'change'}
                    ]
                },
                rubberDialogVisible: false,
                tableDataRubber: [],
                selectionRubber: [],
                dialogVisibleEdit: false,
                formEdit: {
                    pdp_product_batching_classes_plan: [
                        {},
                        {},
                        {}
                    ]
                },
                EditLoading: false,
                dialogVisibleAdd: false,
                formAdd: {},
                rubberDialogParams: {
                    page_size: 100000000,
                    product_no: '',
                    plan_date: ''
                },
                rulesEdit: {
                    equip: {required: true, message: '请选择配料机台', trigger: 'change'},
                    // a: {validator: '', trigger: 'blur'}
                    workRubberType: {required: true, message: '请选择炼胶机类型', trigger: 'change'},
                    product_batching: {required: true, message: '请选择配料小料编码', trigger: 'change'}
                },
                rubberTypeList: [],
                dialogVisibleEditLoading: true,
                addGlueList: [],
                smallMaterialEdit: ''
            }
        },
        created() {
            this.getMachineList()
            this.getGlueList()
            this.getList()

            var _setDate = setDate()
            //设置默认日期
            this.getParams.plan_date = _setDate
            //设置选择胶料的默认当前日期
            this.rubberDialogParams.plan_date = _setDate
        },
        methods: {
            addBatchNum(arr, params) {
                let all = null
                let a = arr && arr[0] ? arr[0][params] : 0
                let b = arr && arr[1] ? arr[1][params] : 0
                let c = arr && arr[2] ? arr[2][params] : 0
                all = Number(a) + Number(b) + Number(c)
                all = Math.round(all * 100) / 100
                return all
            },
            disabledDate(time) {
                var seven = 3600 * 1000 * 24
                var source_data = new Date(this.formCopyData.src_date).getTime()
                var current_data = Date.now()
                if (current_data > source_data) {
                    //选择时间小于当前时间，设置为大于当前时间
                    return time.getTime() < Date.now();
                } else {
                    return time.getTime() < source_data;
                }
            },
            getList() {
                var _this = this
                var tableData = []
                axios.get(this.tableDataUrl, {
                    params: _this.getParams
                }).then(function (response) {
                    tableData = response.data.results || [];
                    if (_this.tableDataTotal !== response.data.count) {
                        _this.tableDataTotal = response.data.count;
                    }
                    _this.getRubberList(true, tableData)
                }).catch(function (error) {
                    this.$message.error('请求错误')
                });
            },
            getMachineList() {
                var _this = this
                axios.get(EquipUrl, {params: {page_size: 100000}}).then(function (response) {
                    _this.machineList = response.data.results || [];
                }).catch(function (error) {
                });
            },
            getGlueList(dev_type) {
                var _dev_type = dev_type ? dev_type : null
                var _this = this
                axios.get(RubberMaterialUrl, {
                    params: {
                        page_size: 1000000,
                        dev_type: _dev_type
                    }
                }).then(function (response) {
                    var glueList = response.data.results || [];
                    //去重
                    var obj = {}
                    var newArr = glueList.reduce(function (item, next) {
                        obj[next.stage_product_batch_no] ? ' ' : obj[next.stage_product_batch_no] = true && item.push(next)
                        return item;
                    }, [])
                    _this.glueList = newArr
                    //新增里面的配料小料编码数据
                    _this.addGlueList = dev_type ? newArr : []
                }).catch(function (error) {
                });
            },
            getRubberList(bool, tableData) {
                /*
                *bool true 获取全部数据
                * 否则 使用在选择胶料弹框内，加入筛选
                 */
                var _this = this
                var params = bool ? {page_size: 100000000} :
                    _this.rubberDialogParams

                if (!bool) {
                    if (!_this.rubberDialogParams.product_no) {
                        _this.rubberDialogParams.product_no = null
                    }
                }
                axios.get(ProductDayPlansUrl, {
                    params
                }).then(function (response) {
                    _this.tableDataRubber = response.data.results || []
                    if (bool) {
                        var arr = response.data.results || []
                        var productDayObj = {}
                        arr.forEach(function (D) {
                            productDayObj[D.id] = D.pdp_product_classes_plan
                        })
                        tableData.forEach(function (D) {
                            if (productDayObj[D.id]) {
                                D.rubber_product_classes_plan = productDayObj[D.id]
                            }
                        })
                        _this.tableData = tableData
                    }
                })
            },
            changeData(val) {
                this.getParams['page'] = 1
                this.getList()
            },
            rowDelete(row) {
                var app = this;
                this.$confirm('此操作将永久删除第' + row.id + '行数据, 是否继续?', '提示', {
                    confirmButtonText: '确定',
                    cancelButtonText: '取消',
                    type: 'warning'
                }).then(() => {
                    axios.delete(this.tableDataUrl + row.id + '/')
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
            copyDataStuff() {
                this.copyDialogVisible = true
            },
            copySubmit() {
                var _this = this
                this.$refs['formCopyData'].validate(function (valid) {
                    if (valid) {
                        _this.loadingBtnCopy = true
                        _this.manageFormError = {}
                        axios.post(MaterialRequisitionsCopy, _this.formCopyData).then(function (response) {
                            _this.copyDialogVisible = false
                            _this.loadingBtnCopy = false

                            this.getParams['page'] = 1
                            this.getList()
                            _this.$message.success('操作成功')
                        }).catch(function (error) {
                            _this.loadingBtnCopy = false
                            if (Object.prototype.toString.call(error.response.data) === '[object Object]') {
                                for (var key in error.response.data) {
                                    if (error.response.data[key]) {
                                        _this.manageFormError[key] = error.response.data[key].join(",")
                                    }
                                }
                            } else {
                                _this.$message.error('操作失败')
                            }
                        });
                    } else {
                        return false;
                    }
                });

            },
            handleCloseCopy(done) {
                if (!this.loadingBtnCopy) {
                    var _this = this
                    setTimeout(function () {
                        _this.$refs.formCopyData.resetFields();
                    }, 300)
                    done()
                }
            },
            sourceDataChange(val) {
                let dst_date = new Date(this.formCopyData.dst_date).getTime()
                let src_date = new Date(this.formCopyData.src_date).getTime()

                if (this.formCopyData.dst_date && dst_date < src_date) {
                    this.formCopyData.dst_date = null
                }
            },
            selectRubber() {
                this.rubberDialogVisible = true
                this.getRubberList(false)
            },
            changeRubberDialog() {
                this.getRubberList(false)
            },
            handleSelectionChange(selection) {
                this.selectionRubber = selection
            },
            rubberDialogSubmit() {
                var _this = this
                var arr = []
                var bool = false
                if (this.selectionRubber.length === 0) {
                    return
                }
                this.selectionRubber.forEach(function (D) {
                    var obj = {}
                    if (!D.newEquip) {
                        _this.$message.info('请选择配料机台！')
                        bool = true
                        return
                    }
                    // 机台
                    obj.equip = D.newEquip
                    // 配料
                    obj.product_batching = D.product_batching
                    let classesArr = []
                    for (var i = 1; i < 4; i++) {
                        classesArr.push({
                            sn: 0,
                            bags_qty: 0,
                            unit: unit
                        })
                    }
                    obj.pdp_product_batching_classes_plan = classesArr
                    obj.plan_date = _this.rubberDialogParams.plan_date
                    // 日计划袋数
                    obj.bags_total_qty = 0
                    // 炼胶日计划id
                    obj.product_day_plan = D.id

                    arr.push(obj)
                })
                if (bool) {
                    return
                }
                axios.post(RubberSelectUrl, arr).then(function (response) {
                    _this.$message.success('添加数据成功')
                    _this.getParams['page'] = 1
                    _this.getList()
                    _this.rubberDialogVisible = false
                }).catch(function (error) {
                    console.log(error, 'error')
                    _this.$message.error('请求错误')
                });
            },
            rowEdit(row) {
                this.dialogVisibleEdit = true
                this.formEdit = row
            },
            getRubberTypeList() {
                var _this = this
                axios.get(GlobalCodesUrl, {params: {class_name: '炼胶机类型', page_size: 1000000}})
                    .then(function (response) {
                        _this.rubberTypeList = response.data.results || []
                        _this.dialogVisibleEditLoading = false
                    }).catch(function (error) {
                    _this.$message.error(error);
                    _this.dialogVisibleEditLoading = false
                });
            },
            handleCloseEdit(done) {
                this.formEdit = {
                    pdp_product_batching_classes_plan: [
                        {},
                        {},
                        {}
                    ]
                }
                this.smallMaterialEdit = ''
                this.$refs.formEdit.resetFields();
                done()
            },
            editSubmit() {
                // console.log(this.formEdit, 888)
                var _this = this
                var obj = {}
                // 机台
                obj.equip = this.formEdit.equip
                // 配料
                obj.product_batching = this.formEdit.product_batching
                let classesArr = []
                this.formEdit.pdp_product_batching_classes_plan.forEach(function (D, index) {
                    classesArr.push({
                        sn: D.sn ? D.sn : 0,
                        bags_qty: D.bags_qty ? D.bags_qty : 0,
                        unit: unit
                    })
                })
                obj.pdp_product_batching_classes_plan = classesArr
                if (this.formEdit.id) {
                    obj.id = this.formEdit.id
                    obj.plan_date = this.formEdit.plan_date_time
                    var allNum = this.addBatchNum(this.formEdit.pdp_product_batching_classes_plan, 'bags_qty')
                    // 日计划袋数
                    obj.bags_total_qty = allNum
                    this.formEdit.bags_total_qty = obj.bags_total_qty
                    // 炼胶日计划id
                    obj.product_day_plan = this.formEdit.product_day_plan
                } else {
                    obj.plan_date = this.getParams.plan_date
                    obj.bags_total_qty = this.formEdit.bags_total_qty ? this.formEdit.bags_total_qty : 0
                }
                var way = this.formEdit.id ? 'put' : 'post'
                var url = this.formEdit.id ? this.tableDataUrl + this.formEdit.id + '/' : this.tableDataUrl
                axios[way](url, obj).then(function (response) {
                    _this.$refs.formEdit.resetFields();
                    _this.formEdit = {
                        pdp_product_batching_classes_plan: [
                            {},
                            {},
                            {}
                        ]
                    }
                    this.smallMaterialEdit = ''
                    _this.$message.success('修改成功')
                    _this.dialogVisibleEdit = false
                    _this.getList()
                }).catch((error) => {
                    _this.$message.error('修改失败')
                });
            },
            addRow() {
                console.log(this.formEdit, 'this.formEdit')
                this.dialogVisibleEdit = true
                if (this.rubberTypeList.length === 0) {
                    this.getRubberTypeList()
                } else {
                    this.dialogVisibleEditLoading = false
                }
            },
            editNumber() {
                var allNumber = 0
                var val = 'pdp_product_batching_classes_plan'
                this.formEdit[val].forEach(function (D) {
                    allNumber += Number(D.bags_qty)
                })
                this.formEdit.bags_total_qty = allNumber
            },
            changeWorkRubberType(val) {
                console.log(val, 'val')
                this.getGlueList(val)
                // this.getSmallMaterial(val)
            },
            handleCloseAdd(done) {
                done()
            },
            addSubmit() {

            },
            handleCloseRubber(done) {
                if (this.$refs.multipleTable) {
                    this.$refs.multipleTable.clearSelection();
                }
                done()
            },
            changeEquip_no() {

            },
            changeProductBatch(val) {
                console.log(this.addGlueList, 'addGlueList')
                console.log(val, 'val')
                var obj = this.addGlueList.filter(function (D) {
                    return D.id === val
                })
                this.smallMaterialEdit = obj[0].batching_weight
            }
        },
        watch: {}
    };
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