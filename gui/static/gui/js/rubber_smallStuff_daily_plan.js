;(function () {

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
                    // equip_no: {},
                    // a: {validator: '', trigger: 'blur'}
                }
            }
        },
        created() {
            this.getMachineList()
            this.getGlueList()
            this.getList()

            //设置选择胶料的默认当前日期
            this.rubberDialogParams.plan_date = new Date()
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
                // console.log(this.getParams, 'this.getParams')
                var tableData = []
                var arr = []
                axios.get(this.tableDataUrl, {
                    params: _this.getParams
                }).then(function (response) {
                    tableData = response.data.results || [];
                    _this.getRubberList(true, tableData)
                })
            },
            getMachineList() {
                var _this = this
                axios.get(EquipUrl, {params: {page_size: 100000}}).then(function (response) {
                    console.log(response.data.results, 'machineList')
                    _this.machineList = response.data.results || [];
                }).catch(function (error) {
                });
            },
            getGlueList() {
                var _this = this
                axios.get(RubberMaterialUrl, {params: {page_size: 100000}}).then(function (response) {
                    var glueList = response.data.results || [];
                    //去重
                    var obj = {}
                    var newArr = glueList.reduce(function (item, next) {
                        obj[next.stage_product_batch_no] ? ' ' : obj[next.stage_product_batch_no] = true && item.push(next)
                        return item;
                    }, [])
                    _this.glueList = newArr
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
                axios.get(ProductDayPlans, {
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
                this.$confirm('此操作将永久删除' + row.category_name + ', 是否继续?', '提示', {
                    confirmButtonText: '确定',
                    cancelButtonText: '取消',
                    type: 'warning'
                }).then(() => {
                    axios.delete(this.tableDataUrl + '/' + row.id + '/')
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
                // console.log(this.selectionRubber, 'selection')
            },
            rowEdit(row) {
                this.dialogVisibleEdit = true
                this.formEdit = row
            },
            handleCloseEdit(done) {
                this.formEdit = {
                    pdp_product_batching_classes_plan: [
                        {},
                        {},
                        {}
                    ]
                }
                done()
            },
            editSubmit() {
                // console.log(this.formEdit, 888)
                var obj = {}
                obj.id = this.formEdit.product_day_plan_id
                obj.equip_no = this.formEdit.equip_id
                obj.equip_no = this.formEdit.equip_id
                var _this = this
                // axios.get(this.tableDataUrl+'/'+this.formEdit.product_day_plan_id+'/', {
                //     params: _this.getParams
                // }).then(function (response) {
                //     tableData = response.data.results || [];
                //     _this.getRubberList(true, tableData)
                // })
            },
            addRow() {
                this.dialogVisibleEdit = true
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

            }
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();