;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {
            return {
                tableDataUrl: MaterialRequisitions,
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
                tableDataRubber: []
            }
        },
        created() {
            this.getMachineList()
            this.getGlueList()
            this.getList()
        },
        methods: {
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
                console.log(this.getParams, 'this.getParams')
                axios.get(this.tableDataUrl, {
                    params: _this.getParams
                }).then(function (response) {
                    _this.tableData = response.data.results || [];
                })
            },
            getMachineList() {
                var _this = this
                axios.get(EquipUrl, {params: {page: 1}}).then(function (response) {
                    _this.machineList = response.data.results || [];
                }).catch(function (error) {
                });
            },
            getGlueList() {
                var _this = this
                axios.get(RubberMaterialUrl, {params: {page: 1}}).then(function (response) {
                    _this.glueList = response.data.results || [];
                    console.log(_this.glueList)
                }).catch(function (error) {
                });
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
                            for (var key in error.response.data) {
                                if (error.response.data[key])
                                    _this.manageFormError[key] = error.response.data[key].join(",")
                            }
                            _this.loadingBtnCopy = false
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
                this.formCopyData.dst_date = null
            },
            selectRubber() {
                this.rubberDialogVisible = true
                // 获取胶料数据

            }
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();