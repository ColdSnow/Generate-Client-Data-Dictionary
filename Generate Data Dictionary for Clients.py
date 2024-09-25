import pandas as pd
import streamlit as st
import re
import base64
import io

# 读取完整的数据字典
@st.cache_data
def load_full_dictionary(uploaded_file):
    if uploaded_file is not None:
        return pd.read_excel(uploaded_file)
    return pd.DataFrame()  # 如果没有上传文件，返回空的DataFrame

 # 读取客户使用表
@st.cache_data
def load_client_table(uploaded_file):
    if uploaded_file is not None:
        return pd.read_csv(uploaded_file)
    return pd.DataFrame()  # 如果没有上传文件，返回空的DataFrame

# 清理表名
def clean_table_name(table_name):
    return re.sub(r'KENVUE|_', '', table_name)


# 处理和合并数据
@st.cache_data
def process_and_merge_data(client_tables, data_dictionary):
    client_tables['cleaned_table_name'] = client_tables['TABLE_NAME'].apply(clean_table_name)
    data_dictionary['cleaned_table_name'] = data_dictionary['table_name'].apply(clean_table_name)
    
    merged_df = pd.merge(client_tables, data_dictionary, 
                         on='cleaned_table_name', 
                         how='inner')
    
    merged_df.drop(columns=['cleaned_table_name'], inplace=True)
    return merged_df

# 生成HTML表格
def generate_html_table(df):
    html = "<table style='width:100%; border-collapse: collapse; margin-bottom: 20px;'>"
    html += "<tr style='background-color: #f2f2f2;'>"
    for col in df.columns:
        html += f"<th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>{col}</th>"
    html += "</tr>"
    
    for _, row in df.iterrows():
        html += "<tr>"
        for value in row:
            html += f"<td style='border: 1px solid #ddd; padding: 8px;'>{value}</td>"
        html += "</tr>"
    
    html += "</table>"
    return html

# 生成完整的HTML文档
def generate_full_html(client_name, tables_data):
    html = f"""
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{client_name} DaaS Data Dictionary</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
            h1 {{ color: #333; }}
            h2 {{ color: #666; margin-top: 30px; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .toc {{ background-color: #f9f9f9; padding: 20px; margin-bottom: 30px; }}
            .toc ul {{ list-style-type: none; padding-left: 20px; }}
        </style>
    </head>
    <body>
        <h1>{client_name} DaaS Data Dictionary</h1>
        <div class="toc">
            <h2>目录</h2>
            <ul>
    """
    
    for table_name in tables_data.keys():
        html += f'<li><a href="#{table_name}">{table_name}</a></li>'
    
    html += """
            </ul>
        </div>
    """
    
    for table_name, table_data in tables_data.items():
        html += f'<h2 id="{table_name}">{table_name}</h2>'
        html += generate_html_table(table_data)
    
    html += """
    </body>
    </html>
    """
    return html

# 修改下载链接函数为下载按钮函数
def get_download_button(html_string, filename):
    b64 = base64.b64encode(html_string.encode()).decode()
    href = f'data:text/html;base64,{b64}'
    return f'<a href="{href}" download="{filename}"><button style="padding: 10px 20px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer;">Download HTML Data Dictionary</button></a>'

# 主函数
def main():
    st.title("Client Data Dictionary Generator")

    # 在侧边栏添加文件上传功能
    st.sidebar.header("Upload Files")
    data_dictionary_file = st.sidebar.file_uploader("upload data dictionary (Excel)", type=['xlsx'])
    client_table_file = st.sidebar.file_uploader("upload client table (CSV)", type=['csv'])

    if data_dictionary_file is not None and client_table_file is not None:
        data_dictionary = load_full_dictionary(data_dictionary_file)
        client_tables = load_client_table(client_table_file)
        
        # 处理和合并数据
        merged_df = process_and_merge_data(client_tables, data_dictionary)

        # 侧边栏：选择客户
        st.sidebar.header("Choose Client")
        clients = sorted(merged_df['CLIENT'].unique())
        selected_client = st.sidebar.selectbox("Client", clients)

        # 根据选择的客户筛选数据
        client_data = merged_df[merged_df['CLIENT'] == selected_client]

        if not client_data.empty:
            # 侧边栏：显示该客户的所有表
            tables = sorted(client_data['TABLE_NAME'].unique())
            total_tables = len(tables)
            st.sidebar.header(f"Table List: (total {total_tables} tables)")
            
            # 全选功能
            select_all = st.sidebar.checkbox("Choose All")
            
            # 使用 session_state 来存储选中的表
            if 'selected_tables' not in st.session_state:
                st.session_state.selected_tables = set()

            # 如果全选被勾选，更新 selected_tables
            if select_all:
                st.session_state.selected_tables = set(tables)
            
            # 在侧边栏中展示所有表名，并允许单独选择
            for table in tables:
                if st.sidebar.checkbox(table, value=table in st.session_state.selected_tables):
                    st.session_state.selected_tables.add(table)
                else:
                    st.session_state.selected_tables.discard(table)

            st.header(f"{selected_client} DaaS Data Dictionary")
            
            # 选择要显示的列
            columns_to_display = ['TABLE_SCHEMA', 'TABLE_NAME', 'column_name', 'notes']
            display_data = client_data[columns_to_display]

            # 存储所有表格数据
            tables_data = {}

            # 生成完整的HTML文档
            for table_name in sorted(display_data['TABLE_NAME'].unique()):
                table_data = display_data[display_data['TABLE_NAME'] == table_name]
                tables_data[table_name] = table_data

            full_html = generate_full_html(selected_client, tables_data)
            
            # 创建下载按钮
            st.markdown(get_download_button(full_html, f"{selected_client}_DaaS_数据字典.html"), unsafe_allow_html=True)
            
            # 显示选中的表格数据
            for table_name in sorted(st.session_state.selected_tables):
                table_data = tables_data[table_name]
                st.subheader(f"{table_name}")
                st.dataframe(table_data)
                st.markdown("<br>", unsafe_allow_html=True)  # 添加一个空行
        else:
            st.write("No available data for the selected client")
    else:
        st.write("Please upload data dictionary and client table files")

if __name__ == "__main__":
    main()

