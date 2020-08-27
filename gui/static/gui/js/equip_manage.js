;(function () {

    var Main = {

        mixins: [BaseMixin, Equip_filter],
        data: function () {

            return {
                dialogCreateEquipVisible: false,
                tableDataUrl: EquipUrl,

                EquipLevel: [],
                EquipLevelOptions: [],
                equip_level: "",

                EquipCategory: [],
                EquipCategoryOptions: [],
                category: "",

                EquipForm: {
                    equip_no: "",
                    equip_name: "",
                    count_flag: true,
                    used_flag: true,
                    description:"",
                    equip_level:"",
                    category:"",
                },
                EquipFormError: {
                    equip_no: "",
                    equip_name: "",
                    count_flag: "",
                    used_flag: "",
                    description:"",
                    equip_level:"",
                    category:"",
                },
                dialogEditEquipVisible: false,
            }
        },
        methods: {

            shiftsEquipLevelChange() {

            },
            shiftsEquipCategoryChange() {

            },

            clearEquipForm: function () {

                this.EquipForm = {
                    equip_no: "",
                    equip_name: "",
                    count_flag: true,
                    used_flag: true,
                    description:"",
                    equip_level:"",
                    category:""
                }
            },
            clearEquipFormError: function () {

                this.EuqipFormError = {
                    equip_no: "",
                    equip_name: "",
                    count_flag: "",
                    used_flag: "",
                    description:"",
                    equip_level:"",
                    category:"",
                }
            },
            showCreateEquipDialog: function () {

                this.clearEquipForm();
                this.clearEquipFormError();
                this.dialogCreateEquipVisible = true;
            },
            handleCreateEquip: function () {

                this.clearEquipFormError();
                var app = this;
                axios.post(EquipUrl, app.EquipForm)
                    .then(function (response) {

                        app.dialogCreateEquipVisible = false;
                        app.$message(app.EquipForm.equip_name + "创建成功");
                        app.currentChange(app.currentPage);

                    }).catch(function (error) {

                    for (var key in app.EquipFormError) {
                        if (error.response.data[key])
                            app.EquipFormError[key] = error.response.data[key].join(",")
                    }
                })
            },
            showEditEquipDialog: function (row) {
                // var row_equip_custom = {};
                // for (var key in row) {
                //     row_equip_custom[key] = row[key];
                //     if(key == "process_name"){
                //         row_equip_custom['category'] = " 工序: "+ row[key]
                //     }
                //     if(key == "equip_type"){
                //         row_equip_custom['category'] = "  设备类型: " + row[key] + row_equip_custom['category']
                //     }
                //     if(key == "category_name"){
                //         row_equip_custom['category'] = "  机型名称: " + row[key] + row_equip_custom['category']
                //     }
                //     if(key == "category_no"){
                //         row_equip_custom['category'] = "  机型编号: " + row[key] + row_equip_custom['category']
                //     }
                //
                // }
                this.clearEquipForm();
                this.clearEquipFormError();
                this.EquipForm = Object.assign({}, row);
                // console.log("==========================================================");
                // console.log(row);
                // console.log("==========================================================");
                this.dialogEditEquipVisible = true;
            },


            handleEditEquip: function () {

                const app = this;

                // console.log("=============================");
                // console.log(this.EquipForm);
                // console.log("=============================");

                axios.put(EquipUrl + this.EquipForm.id + '/', this.EquipForm)
                    .then(function (response) {

                        app.dialogEditEquipVisible = false;
                        app.$message(app.EquipForm.equip_name + "修改成功");
                        app.currentChange(app.currentPage);
                    }).catch(function (error) {
                    for (var key in app.EquipFormError) {

                        if (error.response.data[key])
                            app.EquipFormError[key] = error.response.data[key].join(",")
                    }
                });
            },

            handleEquipDelete: function (row) {

                var app = this;
                this.$confirm('此操作将永久删除' + row.equip_name + ', 是否继续?', '提示', {
                    confirmButtonText: '确定',
                    cancelButtonText: '取消',
                    type: 'warning'
                }).then(() => {

                    axios.delete(EquipUrl + row.id + '/')
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
            EquipCountFlagFormatter: function(row, column) {

                return this.boolFormatter(row.count_flag);
            },
            EquipUsedFlagFormatter: function(row, column) {

                return this.boolFormatter(row.used_flag);
            },

        },

        created: function () {

            var app = this;
            axios.get(EquipLevelGlobalUrl)
                .then(function (response) {

                    app.EquipLevel = response.data.results;
                    // console.log("==================");
                    // console.log(app.Equip);
                    // console.log("==================");
                    for (var i = 0; i < app.EquipLevel.length; ++i) {

                        var label = app.EquipLevel[i]["global_no"] + "——" + app.EquipLevel[i]["global_name"];
                        app.EquipLevelOptions.push({
                            value: app.EquipLevel[i]["id"],
                            label
                        });
                    }
                }).catch(function (error) {

            });
            axios.get(EquipCategoryUrl + '?all=1')
                .then(function (response) {

                    app.EquipCategory = response.data.results;
                    for (var i = 0; i < app.EquipCategory.length; ++i) {

                        var label = "设备类型: " + app.EquipCategory[i]["equip_type_name"] + ";  机型名称: " + app.EquipCategory[i]["category_name"] + ";  机型编号: "+ app.EquipCategory[i]["category_no"] +";  工序: " + app.EquipCategory[i]["equip_process_name"];
                        app.EquipCategoryOptions.push({
                            value: app.EquipCategory[i]["id"],
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