;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {
            return {
                tableDataUrl: MaterialRequisitions,
                machineList: [],
                glueList: []
            }
        },
        created() {
            this.getMachineList()
            this.getGlueList()
            this.getList()
        },
        methods: {
            getList() {
                this.getParams['page'] = 1
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
            copyDataStuff(){
                
            }
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();