import time
import requests
import re
import os
import pandas as pd
from bs4 import BeautifulSoup
from openpyxl import Workbook, load_workbook
import chardet  # 用于检测编码

# 设置请求头，模拟浏览器访问
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}


def detect_encoding(content):
    """检测内容的编码"""
    result = chardet.detect(content)
    return result.get('encoding', 'utf-8')


def get_region():
    """获取行政区划信息"""
    # 这里需要根据网站实际情况返回行政区划的URL映射
    # 由于网站结构可能变化，这里提供一个示例
    region_dict = {
        '西湖区': '/house-a0139/',
        '上城区': '/house-a0140/',
        '下城区': '/house-a0141/',
        '江干区': '/house-a0142/',
        '拱墅区': '/house-a0143/',
        '滨江区': '/house-a0144/',
        '萧山区': '/house-a0145/',
        '余杭区': '/house-a0146/',
        '临安区': '/house-a0147/',
        '富阳区': '/house-a0148/',
        '桐庐县': '/house-a0149/',
        '淳安县': '/house-a0150/',
        '建德市': '/house-a0151/',
    }
    return region_dict


def clean_text(text):
    """清理文本，去除多余空格和换行符"""
    if not text:
        return ''
    # 去除空白字符
    text = text.strip()
    # 替换多个空白字符为单个空格
    text = re.sub(r'\s+', ' ', text)
    return text


def get_first_page(url_1, cookies, headers, adr):
    """获取第一页数据并解析总页数"""
    try:
        response = requests.get(url_1, cookies=cookies, headers=headers, timeout=10)

        if response.status_code != 200:
            print(f"请求失败，状态码：{response.status_code}")
            return None, 0

        # 自动检测编码
        encoding = detect_encoding(response.content)
        response.encoding = encoding

        soup = BeautifulSoup(response.text, 'html.parser', from_encoding=encoding)

        # 获取房屋列表
        shop_list = soup.find('div', class_='shop_list')
        if not shop_list:
            # 尝试其他可能的类名
            shop_list = soup.find('div', class_='list')
            if not shop_list:
                print(f"在 {adr} 区域未找到房屋列表")
                return None, 0

        # 获取当前页的数据
        onepageinfo = []
        house_list = shop_list.find_all('dl')

        for shop in house_list:
            try:
                # 提取各个字段的信息
                title_elem = shop.find('span', class_='tit_shop')
                if not title_elem:
                    title_elem = shop.find('span', class_='tit')
                tit_shop = clean_text(title_elem.text) if title_elem else ''

                tel_elem = shop.find('p', class_='tel_shop')
                if not tel_elem:
                    tel_elem = shop.find('div', class_='tel')
                tel_shop = clean_text(tel_elem.text) if tel_elem else ''

                add_elem = shop.find('p', class_='add_shop')
                if not add_elem:
                    add_elem = shop.find('p', class_='address')
                add_shop = clean_text(add_elem.text) if add_elem else ''

                label_elem = shop.find('p', class_='label')
                if not label_elem:
                    label_elem = shop.find('div', class_='tag')
                label = clean_text(label_elem.text) if label_elem else ''

                price_elem = shop.find('dd', class_='price_right')
                if not price_elem:
                    price_elem = shop.find('div', class_='price')
                price_right = clean_text(price_elem.text) if price_elem else ''

                # 添加到当前页数据列表
                onepageinfo.append([adr, tit_shop, tel_shop, add_shop, label, price_right])
            except Exception as e:
                print(f"解析单个房屋信息时出错: {e}")
                continue

        # 获取总页数
        page_info = soup.find('div', class_='page_al')
        if not page_info:
            page_info = soup.find('div', class_='page')

        pages = 1  # 默认1页

        if page_info:
            page_text = clean_text(page_info.text)
            page_match = re.search(r'共(\d+)页', page_text)
            if page_match:
                pages = int(page_match.group(1))
            else:
                # 尝试其他格式
                page_match = re.search(r'(\d+)\s*页', page_text)
                if page_match:
                    pages = int(page_match.group(1))

        print(f"{adr}区域 - 第1页获取成功，共{pages}页，找到{len(onepageinfo)}条数据")
        return onepageinfo, pages

    except requests.RequestException as e:
        print(f"网络请求失败: {e}")
        return None, 0
    except Exception as e:
        print(f"解析第一页时出错: {e}")
        return None, 0


def get_onepage(url_one, cookies, headers, adr):
    """获取指定页面的数据"""
    try:
        response = requests.get(url_one, cookies=cookies, headers=headers, timeout=10)

        if response.status_code != 200:
            print(f"请求失败: {response.status_code}")
            return None

        # 自动检测编码
        encoding = detect_encoding(response.content)
        response.encoding = encoding

        soup = BeautifulSoup(response.text, 'html.parser', from_encoding=encoding)

        # 获取房屋列表
        shop_list = soup.find('div', class_='shop_list')
        if not shop_list:
            shop_list = soup.find('div', class_='list')
            if not shop_list:
                print(f"未找到房屋列表: {url_one}")
                return None

        onepageinfo = []
        house_list = shop_list.find_all('dl')

        for shop in house_list:
            try:
                title_elem = shop.find('span', class_='tit_shop')
                if not title_elem:
                    title_elem = shop.find('span', class_='tit')
                tit_shop = clean_text(title_elem.text) if title_elem else ''

                tel_elem = shop.find('p', class_='tel_shop')
                if not tel_elem:
                    tel_elem = shop.find('div', class_='tel')
                tel_shop = clean_text(tel_elem.text) if tel_elem else ''

                add_elem = shop.find('p', class_='add_shop')
                if not add_elem:
                    add_elem = shop.find('p', class_='address')
                add_shop = clean_text(add_elem.text) if add_elem else ''

                label_elem = shop.find('p', class_='label')
                if not label_elem:
                    label_elem = shop.find('div', class_='tag')
                label = clean_text(label_elem.text) if label_elem else ''

                price_elem = shop.find('dd', class_='price_right')
                if not price_elem:
                    price_elem = shop.find('div', class_='price')
                price_right = clean_text(price_elem.text) if price_elem else ''

                onepageinfo.append([adr, tit_shop, tel_shop, add_shop, label, price_right])
            except Exception as e:
                print(f"解析房屋信息时出错: {e}")
                continue

        return onepageinfo

    except requests.RequestException as e:
        print(f"网络请求失败: {e}")
        return None
    except Exception as e:
        print(f"解析页面时出错: {e}")
        return None


def save_to_excel_with_pandas(data, filename):
    """使用pandas保存数据到Excel，解决编码问题"""
    try:
        # 创建DataFrame
        columns = ['行政区', '标题', '房屋信息', '地址', '标签', '房价']
        df = pd.DataFrame(data, columns=columns)

        # 保存到Excel，指定编码和引擎
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='杭州二手房数据')

        print(f"数据已成功保存到 {filename}")

    except Exception as e:
        print(f"保存到Excel时出错: {e}")
        # 尝试另一种方式
        try:
            # 创建DataFrame
            columns = ['行政区', '标题', '房屋信息', '地址', '标签', '房价']
            df = pd.DataFrame(data, columns=columns)

            # 使用xlsxwriter引擎
            df.to_excel(filename, index=False, engine='xlsxwriter')
            print(f"数据已成功保存到 {filename} (使用xlsxwriter引擎)")
        except Exception as e2:
            print(f"使用xlsxwriter引擎也失败: {e2}")


def get_data(cookies, headers, filepath):
    """主函数：获取所有数据"""
    try:
        # 获取行政区划信息
        screen_dict = get_region()
        if not screen_dict:
            print("无法获取行政区划信息")
            return

        adrs = list(screen_dict.keys())
        print(f"共发现 {len(adrs)} 个行政区划: {adrs}")

        total_data_count = 0
        all_data = []  # 收集所有数据

        for adr in adrs:
            print(f'\n{"=" * 50}')
            print(f'开始爬取行政区：{adr} - 第1页')

            # 构建第一页URL
            base_url = f'https://hz.esf.fang.com{screen_dict[adr]}i31/'
            print(f'URL: {base_url}')

            # 获取第一页数据
            onepageinfo, pages = get_first_page(base_url, cookies, headers, adr)

            if onepageinfo:
                all_data.extend(onepageinfo)
                total_data_count += len(onepageinfo)
                print(f'第一页完成，已获取 {len(onepageinfo)} 条数据')
            else:
                print(f'{adr}区域第一页没有获取到数据')
                continue

            # 限制最大页数，避免爬取过多
            max_pages = min(pages, 10)  # 每个区域最多爬10页

            # 获取后续页面的数据
            if max_pages > 1:
                for page in range(2, max_pages + 1):
                    print(f'正在爬取 {adr} - 第{page}页')

                    # 构建后续页面URL
                    if 'i31/' in base_url:
                        page_url = base_url.replace('i31/', f'i3{page}/')
                    else:
                        page_url = f'{base_url}i3{page}/'

                    # 获取当前页数据
                    page_data = get_onepage(page_url, cookies, headers, adr)

                    if page_data:
                        all_data.extend(page_data)
                        total_data_count += len(page_data)
                        print(f'第{page}页完成，已获取 {len(page_data)} 条数据')

                    # 添加延迟，避免请求过快
                    time.sleep(2)

            print(f'{adr}行政区爬取完成，当前总数据: {total_data_count}条')

            # 每完成一个区域，保存一次数据
            if all_data:
                save_to_excel_with_pandas(all_data, filepath)

        print(f'\n{"=" * 50}')
        print(f'所有数据爬取完成！')
        print(f'总计爬取数据: {total_data_count}条')
        print(f'数据已保存至: {os.path.abspath(filepath)}')

    except Exception as e:
        print(f"爬取数据过程中出错: {e}")
        # 如果有数据，尝试保存
        if 'all_data' in locals() and all_data:
            save_to_excel_with_pandas(all_data, filepath)


def main():
    """主程序入口"""
    # 设置保存文件路径
    filepath = '杭州二手房数据.xlsx'

    # 设置cookies（根据实际情况修改）
    cookies = {
        # 这里需要添加实际的cookies
        # 可以通过浏览器开发者工具获取
        # 'city': 'hz',
        # 'global_cookie': 'xxxxxx',
    }

    print("开始爬取杭州二手房数据...")
    print(f"数据将保存到: {filepath}")
    print("注意：如果遇到反爬，可能需要添加cookies或使用代理")

    # 开始爬取数据
    get_data(cookies, headers, filepath)


if __name__ == "__main__":
    # 安装chardet库：pip install chardet
    main()